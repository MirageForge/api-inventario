def test_create_category_and_supplier(client, admin_headers):
    # Crear categoría
    cat_res = client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Componentes", "description": "Partes de hardware"}
    )
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    # Crear proveedor
    sup_res = client.post(
        "/api/v1/suppliers",
        headers=admin_headers,
        json={"name": "Distribuidor Mayorista", "email": "info@mayorista.com", "phone": "555-1234"}
    )
    assert sup_res.status_code == 201
    assert sup_res.json()["name"] == "Distribuidor Mayorista"


def test_operator_forbidden_create_category(client, operator_headers):
    response = client.post(
        "/api/v1/categories",
        headers=operator_headers,
        json={"name": "Categoría No Permitida"}
    )
    assert response.status_code == 403


def test_product_lifecycle_and_stock_movements(client, admin_headers, operator_headers):
    # 1. Crear categoría y proveedor
    cat_res = client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={"name": "Almacenamiento", "description": "Discos y memorias"}
    )
    cat_id = cat_res.json()["id"]

    sup_res = client.post(
        "/api/v1/suppliers",
        headers=admin_headers,
        json={"name": "Storage World", "email": "sales@storageworld.com"}
    )
    sup_id = sup_res.json()["id"]

    # 2. Crear Producto con stock inicial de 10
    prod_res = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "SSD-NVME-1TB",
            "name": "Disco SSD NVMe 1TB Kingston",
            "description": "Velocidad de lectura 3500MB/s",
            "category_id": cat_id,
            "supplier_id": sup_id,
            "cost_price": 50.0,
            "unit_price": 85.0,
            "current_stock": 10,
            "min_stock_alert": 5,
        }
    )
    assert prod_res.status_code == 201
    prod = prod_res.json()
    prod_id = prod["id"]
    assert prod["current_stock"] == 10
    assert prod["is_low_stock"] is False

    # 3. Entrada de mercancía (IN): +15 unidades
    mov_in = client.post(
        "/api/v1/movements",
        headers=operator_headers,
        json={
            "product_id": prod_id,
            "movement_type": "IN",
            "quantity": 15,
            "reference_number": "REM-00123",
            "notes": "Recepción de lote nuevo"
        }
    )
    assert mov_in.status_code == 201
    assert mov_in.json()["previous_stock"] == 10
    assert mov_in.json()["new_stock"] == 25

    # 4. Salida de mercancía (OUT): -7 unidades
    mov_out = client.post(
        "/api/v1/movements",
        headers=operator_headers,
        json={
            "product_id": prod_id,
            "movement_type": "OUT",
            "quantity": 7,
            "reference_number": "PEDIDO-445",
            "notes": "Entrega a cliente"
        }
    )
    assert mov_out.status_code == 201
    assert mov_out.json()["new_stock"] == 18

    # 5. Salida con stock insuficiente (intentar sacar 50 habiendo 18) -> debe fallar con 400
    mov_fail = client.post(
        "/api/v1/movements",
        headers=operator_headers,
        json={
            "product_id": prod_id,
            "movement_type": "OUT",
            "quantity": 50,
            "notes": "Pedido excesivo"
        }
    )
    assert mov_fail.status_code == 400
    assert "insuficiente" in mov_fail.json()["detail"].lower()

    # 6. Ajuste físico de inventario (ADJUSTMENT) a 3 unidades (dispara alerta de stock bajo)
    mov_adj = client.post(
        "/api/v1/movements",
        headers=operator_headers,
        json={
            "product_id": prod_id,
            "movement_type": "ADJUSTMENT",
            "quantity": 3,
            "notes": "Auditoría de almacén: recuento físico"
        }
    )
    assert mov_adj.status_code == 201
    assert mov_adj.json()["new_stock"] == 3

    # 7. Verificar producto actualizado y alerta de stock bajo
    prod_check = client.get(f"/api/v1/products/{prod_id}", headers=operator_headers).json()
    assert prod_check["current_stock"] == 3
    assert prod_check["is_low_stock"] is True

    # 8. Comprobar Dashboard y métricas
    dash_res = client.get("/api/v1/dashboard/summary", headers=operator_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["total_products"] == 1
    assert dash_data["low_stock_products_count"] == 1
    assert dash_data["total_units_in_stock"] == 3
    assert dash_data["total_inventory_valuation_cost"] == 3 * 50.0
    assert dash_data["total_inventory_valuation_retail"] == 3 * 85.0
    assert len(dash_data["recent_movements"]) >= 3

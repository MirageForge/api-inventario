"""
Script para poblar la base de datos de inventario con datos de prueba realistas.
Ejecución: python seed_data.py
"""
from app.database import engine, Base, SessionLocal
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.movement import InventoryMovement, MovementType
from app.security import get_password_hash


def seed():
    print("Inicializando esquema de base de datos...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Crear Usuarios
        print("Creando usuarios...")
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@inventario.com",
                full_name="Administrador Principal",
                hashed_password=get_password_hash("Admin123!"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)

        operator = db.query(User).filter(User.username == "operador1").first()
        if not operator:
            operator = User(
                username="operador1",
                email="operador@inventario.com",
                full_name="Carlos Operador",
                hashed_password=get_password_hash("Operador123!"),
                role=UserRole.OPERATOR,
                is_active=True
            )
            db.add(operator)

        db.commit()
        db.refresh(admin)
        db.refresh(operator)

        # 2. Categorías
        print("Creando categorías...")
        cat_data = [
            ("Electrónica y Cómputo", "Computadoras portátiles, de escritorio y componentes principales"),
            ("Periféricos y Accesorios", "Teclados, mouse, monitores, cables y adaptadores"),
            ("Mobiliario de Almacén y Oficina", "Escritorios, sillas ergonómicas y estanterías"),
            ("Redes y Conectividad", "Routers, switches de red, puntos de acceso y cableado estructurado"),
        ]
        categories = {}
        for name, desc in cat_data:
            cat = db.query(Category).filter(Category.name == name).first()
            if not cat:
                cat = Category(name=name, description=desc)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            categories[name] = cat

        # 3. Proveedores
        print("Creando proveedores...")
        sup_data = [
            ("Tech Wholesale Corp", "Elena Rostova", "contacto@techwholesale.com", "+52 55 1234 5678", "Av. Insurgentes Sur 1200, CDMX"),
            ("Global Supply Logistics", "Roberto Martínez", "ventas@globalsupply.io", "+52 81 9876 5432", "Parque Industrial Apodaca, N.L."),
            ("Mobiliario & Confort S.A.", "Sofía Andrade", "pedidos@mobiliarioconfort.com", "+52 33 5555 1122", "Zona Industrial Guadalajara, Jal."),
        ]
        suppliers = {}
        for name, contact, email, phone, addr in sup_data:
            sup = db.query(Supplier).filter(Supplier.name == name).first()
            if not sup:
                sup = Supplier(name=name, contact_name=contact, email=email, phone=phone, address=addr)
                db.add(sup)
                db.commit()
                db.refresh(sup)
            suppliers[name] = sup

        # 4. Productos
        print("Creando productos...")
        prod_data = [
            {
                "sku": "LAP-TP-001",
                "name": "Laptop Lenovo ThinkPad T14 Gen 4",
                "description": "Intel Core i7 13va Gen, 16GB RAM, 512GB SSD NVMe, Pantalla 14 FHD+",
                "category": "Electrónica y Cómputo",
                "supplier": "Tech Wholesale Corp",
                "cost_price": 950.00,
                "unit_price": 1399.00,
                "current_stock": 18,
                "min_stock_alert": 5,
            },
            {
                "sku": "MON-DELL-27",
                "name": "Monitor Dell UltraSharp 27 4K",
                "description": "Panel IPS 4K UHD 3840x2160, USB-C 90W Power Delivery, calibración 99% sRGB",
                "category": "Periféricos y Accesorios",
                "supplier": "Tech Wholesale Corp",
                "cost_price": 380.00,
                "unit_price": 549.99,
                "current_stock": 25,
                "min_stock_alert": 8,
            },
            {
                "sku": "TEC-MEC-RGB",
                "name": "Teclado Mecánico Inalámbrico Pro",
                "description": "Switches mecánicos táctiles, retroiluminación RGB por tecla, conexión Bluetooth y 2.4GHz",
                "category": "Periféricos y Accesorios",
                "supplier": "Global Supply Logistics",
                "cost_price": 45.00,
                "unit_price": 89.90,
                "current_stock": 42,
                "min_stock_alert": 15,
            },
            {
                "sku": "SIL-ERG-PRO",
                "name": "Silla Ergonómica Mesh Transpirable",
                "description": "Soporte lumbar ajustable 3D, reposabrazos 4D, base de aluminio reforzada",
                "category": "Mobiliario de Almacén y Oficina",
                "supplier": "Mobiliario & Confort S.A.",
                "cost_price": 140.00,
                "unit_price": 279.00,
                "current_stock": 12,
                "min_stock_alert": 6,
            },
            {
                "sku": "NET-ROUT-AX6",
                "name": "Router Wi-Fi 6 Dual Band Gigabit",
                "description": "Velocidad combinada hasta 3000 Mbps, soporte OFDMA y MU-MIMO, 4 puertos Gigabit LAN",
                "category": "Redes y Conectividad",
                "supplier": "Global Supply Logistics",
                "cost_price": 60.00,
                "unit_price": 115.00,
                "current_stock": 30,
                "min_stock_alert": 10,
            },
            {
                "sku": "CAB-HDMI-21",
                "name": "Cable HDMI 2.1 Ultra High Speed 2m",
                "description": "Ancho de banda 48Gbps, soporte para resolución 8K@60Hz y 4K@120Hz con eARC",
                "category": "Periféricos y Accesorios",
                "supplier": "Tech Wholesale Corp",
                "cost_price": 6.50,
                "unit_price": 18.00,
                "current_stock": 3,  # ALERTA DE STOCK BAJO (Stock 3 <= Alerta 15)
                "min_stock_alert": 15,
            },
        ]

        products = {}
        for p in prod_data:
            existing_prod = db.query(Product).filter(Product.sku == p["sku"]).first()
            if not existing_prod:
                new_prod = Product(
                    sku=p["sku"],
                    name=p["name"],
                    description=p["description"],
                    category_id=categories[p["category"]].id,
                    supplier_id=suppliers[p["supplier"]].id,
                    cost_price=p["cost_price"],
                    unit_price=p["unit_price"],
                    current_stock=p["current_stock"],
                    min_stock_alert=p["min_stock_alert"],
                    is_active=True
                )
                db.add(new_prod)
                db.commit()
                db.refresh(new_prod)
                products[p["sku"]] = new_prod

                # Registrar movimiento de lote inicial
                mov_init = InventoryMovement(
                    product_id=new_prod.id,
                    user_id=admin.id,
                    movement_type=MovementType.IN,
                    quantity=new_prod.current_stock,
                    previous_stock=0,
                    new_stock=new_prod.current_stock,
                    unit_cost=new_prod.cost_price,
                    reference_number=f"INICIAL-{new_prod.sku}",
                    notes="Carga de stock inicial al sistema"
                )
                db.add(mov_init)
                db.commit()
            else:
                products[p["sku"]] = existing_prod

        # 5. Registrar algunos movimientos adicionales de prueba
        print("Registrando movimientos adicionales...")
        prod_laptop = products.get("LAP-TP-001")
        if prod_laptop:
            # Salida por venta
            mov_sale = InventoryMovement(
                product_id=prod_laptop.id,
                user_id=operator.id,
                movement_type=MovementType.OUT,
                quantity=2,
                previous_stock=prod_laptop.current_stock,
                new_stock=prod_laptop.current_stock - 2,
                unit_cost=prod_laptop.cost_price,
                reference_number="FACT-2026-0041",
                notes="Venta directa a cliente corporativo"
            )
            prod_laptop.current_stock -= 2
            db.add(mov_sale)
            db.commit()

        print("\nSembrado de datos finalizado con exito!")
        print("Credenciales disponibles:")
        print(" -> Administrador: usuario 'admin' | contrasena 'Admin123!'")
        print(" -> Operador:      usuario 'operador1' | contrasena 'Operador123!'")

    finally:
        db.close()


if __name__ == "__main__":
    seed()

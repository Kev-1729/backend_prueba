from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from sqlalchemy import func, text
from app.domain.ports.operation_repository import OperationRepository
from app.domain.models.invoice import Invoice
from .models import Operacion, Factura, Empresa
from datetime import datetime

class PostgreSQLOperationRepository(OperationRepository):
    def __init__(self, db: Session):
        self.db = db

    def _find_or_create_company(self, ruc: str, name: str) -> Optional[Empresa]:
        if not ruc: return None
        empresa = self.db.query(Empresa).filter(Empresa.ruc == ruc).first()
        if not empresa:
            empresa = Empresa(ruc=ruc, razon_social=name)
            self.db.add(empresa)
            self.db.flush()
        return empresa


    def find_by_id(self, operation_id: str) -> Optional[Operacion]:
        """Busca una operación por su ID en la tabla 'operaciones'."""
        return self.db.query(Operacion).filter(Operacion.id == operation_id).first()


    def save_full_operation(self, metadata: dict, drive_url: str, invoices: List[Invoice], cavali_results_map: Dict[str, Any]) -> str:
        """
        Implementación final que genera el ID internamente antes de guardar.
        """
        # 1. Generar el nuevo ID de operación
        today_str = datetime.now().strftime('%Y%m%d')
        id_prefix = f"OP-{today_str}-"
        last_id_today = self.db.query(func.max(Operacion.id)).filter(Operacion.id.like(f"{id_prefix}%")).scalar()
        next_number = int(last_id_today.split('-')[-1]) + 1 if last_id_today else 1
        operation_id = f"{id_prefix}{next_number:03d}"
        print(f"Nuevo ID de Operación generado: {operation_id}")

        # 2. Determinar datos de la operación (cliente, sumatorias)
        if not invoices:
            raise ValueError("No se puede guardar una operación sin facturas.")
        
        primer_cliente = self._find_or_create_company(invoices[0].client_ruc, invoices[0].client_name)
        monto_sumatoria = sum(inv.total_amount for inv in invoices)
        moneda_sumatoria = invoices[0].currency

        # 3. Crear la operación principal
        email = metadata.get('user_email', 'unknown@example.com')
        nombre_ejecutivo = email.split('@')[0].replace('.', ' ').title()
        
        db_operacion = Operacion(
            id=operation_id, cliente_ruc=primer_cliente.ruc,
            email_usuario=email, nombre_ejecutivo=nombre_ejecutivo,
            url_carpeta_drive=drive_url, monto_sumatoria_total=monto_sumatoria,
            moneda_sumatoria=moneda_sumatoria
        )
        self.db.add(db_operacion)
        self.db.flush()

        # 4. Crear las facturas asociadas
        for inv in invoices:
            deudor = self._find_or_create_company(inv.debtor_ruc, inv.debtor_name)
            cavali_data = cavali_results_map.get(inv.document_id, {})
            
            db_factura = Factura(
                id_operacion=operation_id,
                numero_documento=inv.document_id,
                deudor_ruc=deudor.ruc if deudor else None,
                fecha_emision=inv.issue_date,
                fecha_vencimiento=inv.due_date,
                moneda=inv.currency,
                monto_total=inv.total_amount,
                monto_neto=inv.net_amount,
                mensaje_cavali=cavali_data.get("message"),
                id_proceso_cavali=cavali_data.get("process_id"),
            )
            self.db.add(db_factura)
            
        return operation_id

    def generar_siguiente_id_operacion(self) -> str:
        """
        Implementación que genera el ID de operación único y secuencial.
        """
        today_str = datetime.now().strftime('%Y%m%d')
        id_prefix = f"OP-{today_str}-"
        
        # Busca el último ID de hoy en la base de datos
        # Usamos 'text' para poder usar funciones de string de PostgreSQL
        last_id_today = self.db.query(func.max(Operacion.id))\
            .filter(Operacion.id.like(f"{id_prefix}%"))\
            .scalar()
        
        if last_id_today:
            # Si encuentra uno, extrae el número, lo convierte a entero y le suma 1
            last_number = int(last_id_today.split('-')[-1])
            next_number = last_number + 1
        else:
            # Si es el primero del día, empieza en 1
            next_number = 1
            
        # Formatea el nuevo ID con 3 dígitos (ej. 001, 012, 123)
        return f"{id_prefix}{next_number:03d}"
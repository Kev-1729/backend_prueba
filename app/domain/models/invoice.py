# app/domain/models/invoice.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date

class Invoice(BaseModel):
    """
    Representa los datos extraídos de una factura XML y enriquecidos
    durante el proceso. Utiliza la sintaxis de Pydantic V2.
    """
    # --- Campos del XML ---
    document_id: str
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: str
    total_amount: float
    net_amount: float
    debtor_name: str
    debtor_ruc: str
    client_name: str
    client_ruc: str

    # --- Campos opcionales que se añaden durante el proceso ---
    cavali_message: Optional[str] = None
    cavali_process_id: Optional[str] = None
    cavali_service_id: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True, # Permite crear el modelo usando los alias
        from_attributes=True,  # Reemplaza a orm_mode=True, permite leer desde objetos
        extra='allow'          # Permite añadir atributos extra al modelo dinámicamente
    )
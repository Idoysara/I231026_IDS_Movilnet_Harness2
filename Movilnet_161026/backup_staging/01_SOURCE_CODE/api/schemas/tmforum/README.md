# TM Forum Open API Schemas — Especificaciones de Referencia
## Proyecto: `AI_Movilnet_300926`
**Fuente Oficial:** [github.com/tmforum-rand/Open_API_And_Data_Model](https://github.com/tmforum-rand/Open_API_And_Data_Model)  
**Licencia:** Apache 2.0 (Open Standard)  

---

## 1. Mapeo de Entidades TM Forum aplicables a Movilnet

| Estándar TM Forum | Dominio Telco | Aplicación en el Modelo de Datos Movilnet |
|:---|:---|:---|
| **TMF620** | Product Catalog Management | Tabla `plans` y paquetes de datos 4GMAX (Inteliplan, Conectados). |
| **TMF678** | Customer Bill Management | Tabla `account_statements` (saldos, corte, consumo de megas). |
| **TMF632** | Party Management | Tabla `subscribers` (titulares de la línea, cédula, RIF, correo). |
| **TMF676** | Payment Management | Tabla `recharge_transactions` (pagos C2P, transferencias, canales). |
| **TMF680** | Recommendation API | Motor de sugerencia proactiva de paquetes cuando el cupo está bajo. |

---

## 2. Esquema Simplificado TMF678 (Customer Bill - Estado de Cuenta)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TMF678_CustomerBill_Movilnet",
  "type": "object",
  "properties": {
    "id": { "type": "string", "format": "uuid" },
    "billNo": { "type": "string" },
    "billingPeriod": {
      "type": "object",
      "properties": {
        "startDateTime": { "type": "string", "format": "date-time" },
        "endDateTime": { "type": "string", "format": "date-time" }
      }
    },
    "billDate": { "type": "string", "format": "date" },
    "paymentDueDate": { "type": "string", "format": "date" },
    "amountDue": {
      "type": "object",
      "properties": {
        "unit": { "type": "string", "default": "VES" },
        "value": { "type": "number" }
      }
    },
    "remainingDataQuotaMB": { "type": "number" },
    "remainingVoiceMinutes": { "type": "integer" }
  },
  "required": ["id", "billNo", "paymentDueDate", "amountDue"]
}
```

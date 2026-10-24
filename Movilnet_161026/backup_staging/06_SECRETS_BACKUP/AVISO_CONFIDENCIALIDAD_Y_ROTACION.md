# 🔐 Aviso de Seguridad y Rotación de Secretos
Este paquete contiene configuraciones de entorno (.env).
En caso de traspaso a servidores del cliente:
1. Reemplazar API Keys de Gemini / Groq / OpenAI por las del cliente.
2. Rotar el JWT Secret y API Key de Movilnet Core.
3. Actualizar credenciales de PostgreSQL si difieren del contenedor estándar.

# Primer CRM para Windows

Aplicación de escritorio en español conectada al CRUD de clientes en Google Sheets mediante Apps Script. Sin servidor local ni navegador.

## Descargar el ejecutable

En GitHub abre **Actions → Windows executable → última ejecución correcta → Artifacts → PrimerCRM-Windows**. Descarga el ZIP, extráelo y abre `PrimerCRM.exe`. Necesitas iniciar sesión en GitHub para descargar artifacts. Cada push a main compila una nueva versión; los artifacts duran 30 días y pueden regenerarse ejecutando el workflow manualmente.

El ejecutable no está firmado digitalmente. Windows puede mostrar una advertencia de editor desconocido. No requiere instalar Python cuando se usa el ejecutable.

## Conectar

1. Abre la aplicación en Windows 10/11 de 64 bits.
2. En Configuración, confirma la URL `/exec` de tu Apps Script (puedes reemplazar la precargada si creaste otra implementación).
3. Ingresa el **valor** de `API_KEY` del script y pulsa **Verificar y guardar**.
4. La aplicación consulta la API; si la conexión funciona, guarda la configuración y muestra los clientes.

La aplicación requiere internet y una implementación que permita acceso anónimo, ejecutada como el propietario. La clave se envía en el cuerpo JSON por HTTPS. La hoja puede mantenerse privada. Se usa exactamente el contrato anterior: `action: list/get/create/update/delete`, `data`, `id`, `limit`, `offset`, `q` y `estado`. También se comprueba `ok` en la respuesta, aunque HTTP sea 200.

## Funciones

- Lista de clientes, 50 por página, con búsqueda y filtro de estado.
- Crear y editar todos los campos CRM del backend.
- Doble clic para consultar el registro actual y editarlo.
- Eliminación con confirmación explícita.
- Errores visibles, conexiones en segundo plano y espera máxima de 45 segundos por operación de red.
- Sin reintentos automáticos de escritura para evitar duplicar altas cuando la respuesta se pierde. Si guardar falla por conexión, actualiza la lista antes de repetir.

## Cifrado de la clave

`%LOCALAPPDATA%\PrimerCRM\credential.dpapi` contiene la clave cifrada mediante **Windows DPAPI**, en el ámbito del usuario actual. `config.json` contiene únicamente la URL. No hay contraseña de descifrado incrustada, claves reales en el código, ni secretos en GitHub Actions. No se registra la clave en logs. El campo de entrada la oculta y no permite recuperar visualmente la guardada.

DPAPI protege el secreto en reposo frente a otros usuarios; procesos ejecutados bajo tu mismo usuario y administradores con control del equipo podrían acceder a él. La clave debe estar disponible temporalmente en memoria para llamar a la API. No copies el archivo cifrado a otra cuenta o equipo: introduce la clave nuevamente. Para rotarla, cambia el valor en Apps Script y vuelve a guardarla en Configuración. Para borrar la configuración local, cierra la aplicación y elimina la carpeta PrimerCRM en LocalAppData.

Referencia: https://learn.microsoft.com/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata

## Ejecutar desde código

Instala Python 3.12 para Windows con Tkinter (incluido en el instalador oficial):

```powershell
python app.py
```

No hay dependencias externas de ejecución. Para compilar localmente:

```powershell
python -m pip install pyinstaller==6.16.0
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PrimerCRM app.py
```

Salida: `dist\PrimerCRM.exe`.

## Pruebas

```powershell
python -m unittest -v
```

Incluye validación de URL, contrato POST, errores JSON/HTML, destinos de redirección, cifrado/descifrado DPAPI y construcción de ventana. Las dos últimas pruebas requieren Windows y se ejecutan en CI. Las pruebas no modifican Google Sheets. La integración real requiere tu clave local; no se incluye una clave de prueba operativa.

No ofrece roles individuales ni historial de cambios; quien tenga la API key puede usar todas las operaciones que permite el backend. Los datos de clientes se mantienen en memoria mientras la aplicación está abierta, sin copia local persistente.

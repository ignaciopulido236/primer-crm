# Primer CRM · Go + Wails

CRM de escritorio Windows en Go. Google Sheets sigue siendo la base de datos a través del Apps Script existente; no hay cambios en el contrato ni necesidad de volver a publicar el backend. La interfaz usa HTML/CSS/JavaScript embebidos en el ejecutable mediante Wails. No requiere Python ni un servidor web local.

## Descargar

Abre **Actions → Windows executable → última ejecución correcta → Artifacts → PrimerCRM-Go-Windows**. Descarga y extrae el ZIP, y abre `PrimerCRM.exe`. Los artifacts requieren sesión de GitHub y se conservan 30 días. El programa no está firmado digitalmente.

## Primer inicio

1. Abre Configuración, confirma la URL `/exec` que ya funciona con curl e ingresa tu API key.
2. Pulsa **Verificar y guardar**. Se consulta la API antes de guardar.
3. Crea, busca, filtra, edita y elimina clientes desde la aplicación.

La URL precargada puede sustituirse si creaste otra implementación. Se requiere internet y acceso anónimo de la aplicación web, ejecutada como el propietario. La API key se envía únicamente por POST sobre HTTPS y no se devuelve al frontend después de guardarla.

## Compilar en Windows

Instala **Go 1.24.2 o posterior** desde https://go.dev/dl/ y **Microsoft Edge WebView2 Runtime** si tu equipo no lo tiene. Cierra y abre PowerShell después de instalar Go.

Desde la carpeta del repositorio:

```powershell
go version
go mod tidy
go test -v ./...
go install github.com/wailsapp/wails/v2/cmd/wails@v2.10.2
& "$(go env GOPATH)\bin\wails.exe" build -clean -platform windows/amd64 -webview2 download
```

Salida: `build\bin\PrimerCRM.exe`. La opción de WebView2 ofrece instalar su runtime si no está disponible. Para compilar también puedes usar el workflow de GitHub Actions; no requiere preparar herramientas en tu equipo. No se necesita Node/npm porque esta interfaz usa archivos estáticos sin un paso de bundling.

Para desarrollo: `& "$(go env GOPATH)\bin\wails.exe" dev`.

## Seguridad

El backend Go cifra la clave usando **Windows DPAPI** con ámbito del usuario actual. En `%APPDATA%\PrimerCRM\connection-go.json` se guardan la URL y bytes cifrados codificados en base64. Base64 es únicamente la representación de los bytes: el cifrado real lo aplica DPAPI. No se incluyen claves reales en el repositorio ni en el ejecutable. Los archivos temporales también contienen únicamente el secreto cifrado; URL y secreto se reemplazan juntos de forma atómica.

La clave se descifra en memoria para las llamadas HTTP. DPAPI no impide acceso a procesos que ya controlen tu usuario de Windows. No compartas la API key ni copies la configuración entre usuarios/equipos: ingrésala de nuevo. Para rotarla, cambia la propiedad en Apps Script y actualiza Configuración. Para olvidar la clave, cierra la aplicación y elimina el archivo de configuración.

La configuración de la versión Python no se migra automáticamente y permanece intacta; introduce la clave una vez en la nueva versión Go.

## Funciones y límites

- CRUD completo de los 13 campos editables; ID y fechas los gestiona el backend.
- Búsqueda por nombre, email, teléfono o empresa; filtro por estado; páginas de 50 registros.
- Consulta fresca antes de editar, confirmación de borrado y escape seguro de datos en el DOM.
- Operaciones de red en segundo plano; tiempo máximo de 45 segundos; lectura de errores JSON incluso con HTTP 200.
- Redirecciones restringidas a dominios de Apps Script. No se reintentan escrituras automáticamente: si pierdes conexión al guardar, actualiza antes de repetir.
- No persiste clientes en disco ni añade roles, historial o sincronización sin conexión.

## Pruebas

`go test -v ./...` prueba contrato HTTP, validación de URL, errores de API/HTML, exclusión de la clave en configuración pública, cifrado y descifrado DPAPI y reemplazo atómico. Ejecutar en Windows. Las pruebas no modifican clientes reales. El workflow compila el ejecutable en Windows y ejecuta `go vet`.

Referencias: https://wails.io/docs/gettingstarted/installation/ y https://learn.microsoft.com/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata

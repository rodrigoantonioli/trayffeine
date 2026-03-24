#ifndef AppVersion
  #define AppVersion "0.3.2"
#endif

#ifndef SourceRoot
  #define SourceRoot "..\..\"
#endif

#ifndef OutputDir
  #define OutputDir "{#SourceRoot}\dist\installer"
#endif

#define MyAppName "Trayffeine"
#define MyAppVersion AppVersion
#define MyAppPublisher "Rodrigo Antonioli"
#define MyAppURL "https://github.com/rodrigoantonioli/trayffeine"
#define MyAppExeName "Trayffeine.exe"

[Setup]
AppId={{70B06B9D-D607-4E77-9DC6-3C7C81C6C3D3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir={#OutputDir}
OutputBaseFilename=Trayffeine-Setup-{#MyAppVersion}
SetupIconFile={#SourceRoot}\assets\trayffeine-app.ico

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "startmenu"; Description: "Criar atalho no menu Iniciar"; Flags: checkedonce

[Files]
Source: "{#SourceRoot}\dist\Trayffeine\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent

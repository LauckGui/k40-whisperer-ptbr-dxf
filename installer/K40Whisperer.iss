#define AppName "K40 Whisperer"
#define AppVersion "1.1.1"
#define AppPublisher "K40 Whisperer"
#define AppExeName "K40 Whisperer.exe"
#ifndef AppSource
#define AppSource "..\release\K40 Whisperer"
#endif
#ifndef InstallerOutputDir
#define InstallerOutputDir "..\dist\installer"
#endif

[Setup]
AppId={{8DCE73AD-1EB6-4EE8-9B59-3B6921E01227}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
PrivilegesRequired=lowest
OutputDir={#InstallerOutputDir}
OutputBaseFilename=K40-Whisperer-Setup-{#AppVersion}-x64
SetupIconFile=..\scorchworks.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\gpl-3.0.txt

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\.k40p"; ValueType: string; ValueData: "K40Whisperer.Project"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\K40Whisperer.Project"; ValueType: string; ValueData: "Projeto do K40 Whisperer"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\K40Whisperer.Project\DefaultIcon"; ValueType: string; ValueData: "{app}\{#AppExeName},0"
Root: HKCU; Subkey: "Software\Classes\K40Whisperer.Project\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Executar {#AppName}"; Flags: nowait postinstall skipifsilent

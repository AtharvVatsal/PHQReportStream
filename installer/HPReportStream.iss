; HP Police ReportStream Installer Script
; Version: 4.0.0

#define MyAppName "HP Police ReportStream"
#define MyAppVersion "4.0.0"
#define MyAppPublisher "Atharv Vatsal"
#define MyAppURL "https://hppolice.gov.in"
#define MyAppExeName "HPReportStream.exe"
#define MyAppCopyright "Copyright (C) 2024 Atharv Vatsal"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright={#MyAppCopyright}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\output
OutputBaseFilename=HPReportStream_Setup_v{#MyAppVersion}
SetupIconFile=A:\Work\PHQReportStream\PHQReportStream\assets\Himachal_Pradesh_Police_Logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardImageFile=A:\Work\PHQReportStream\PHQReportStream\assets\Himachal_Pradesh_Police_Logo.png
WizardSmallImageFile=A:\Work\PHQReportStream\PHQReportStream\assets\Himachal_Pradesh_Police_Logo.png
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Core application - always installed
Name: "core"; Description: "HP Police ReportStream Application"; GroupDescription: "Installation Components:"; Flags: checkedonce

; Desktop shortcut
Name: "desktopicon"; Description: "Create Desktop Shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

; Ollama for LLM mode
Name: "ollama"; Description: "Install Ollama (Required for LLM Mode) - ~100MB"; GroupDescription: "AI Components:"; Flags: unchecked

; Download Mistral model
Name: "mistral"; Description: "Download Mistral AI Model (~4GB)"; GroupDescription: "AI Components:"; Flags: unchecked

[Files]
Source: "..\dist\HPReportStream\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Tasks: core

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: core
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch HP Police ReportStream"; Flags: nowait postinstall skipifsilent; Tasks: core

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Check if Ollama is already installed
function IsOllamaInstalled(): Boolean;
var
  s: String;
begin
  Result := False;
  if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Ollama', 'InstallPath', s) then
    Result := True
  else if RegQueryStringValue(HKEY_CURRENT_USER, 'SOFTWARE\Ollama', 'InstallPath', s) then
    Result := True
  else if FileExists(ExpandConstant('{pf}\Ollama\ollama.exe')) then
    Result := True
  else if FileExists(ExpandConstant('{localappdata}\Ollama\ollama.exe')) then
    Result := True;
end;

// Check if Mistral model exists
function IsMistralDownloaded(): Boolean;
var
  s: String;
begin
  Result := False;
  if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Ollama', 'InstallPath', s) then
  begin
    if FileExists(AddBackslash(s) + 'models\manifests\registry.ollama.ai\library\mistral') then
      Result := True;
  end;
end;

procedure InstallOllama();
var
  ResultCode: Integer;
begin
  // Open Ollama download page
  ShellExec('open', 'https://ollama.com/download/windows', '', '', SW_SHOW, ewNoWait, ResultCode);
  
  MsgBox('Ollama download page has opened in your browser.' + #13#10 + #13#10 +
         'Please download and run "OllamaSetup.exe" to install Ollama.' + #13#10 + #13#10 +
         'After installation, you can download the Mistral model.',
         mbInformation, MB_OK);
end;

procedure DownloadMistral();
var
  OllamaPath: String;
  s: String;
  ResultCode: Integer;
begin
  // Find Ollama installation
  OllamaPath := '';
  if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Ollama', 'InstallPath', s) then
    OllamaPath := s
  else if RegQueryStringValue(HKEY_CURRENT_USER, 'SOFTWARE\Ollama', 'InstallPath', s) then
    OllamaPath := s;

  if OllamaPath = '' then
  begin
    MsgBox('Ollama not found. Please install Ollama first.',
           mbError, MB_OK);
    Exit;
  end;

  // Pull mistral model
  MsgBox('Downloading Mistral model (~4GB)...' + #13#10 +
         'This may take several minutes.',
         mbInformation, MB_OK);

  Exec(AddBackslash(OllamaPath) + 'ollama.exe', 'pull mistral', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  if ResultCode = 0 then
    MsgBox('Mistral model downloaded successfully!' + #13#10 + #13#10 +
           'LLM mode is now ready to use.', mbInformation, MB_OK)
  else
    MsgBox('Failed to download Mistral model.' + #13#10 + #13#10 +
           'You can manually run: ollama pull mistral', mbError, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Show welcome message with options
    MsgBox('HP Police ReportStream has been installed!' + #13#10 + #13#10 +
           'Available AI Modes:' + #13#10 +
           '- Fast Mode: Regex + Typo Dictionary (no extra installation)' + #13#10 +
           '- Accurate Mode: spaCy NER + DistilBERT (included)' + #13#10 +
           '- LLM Mode: Ollama + Mistral (requires installation)',
           mbInformation, MB_OK);

    // If Ollama task selected
    if IsTaskSelected('ollama') then
    begin
      if not IsOllamaInstalled() then
        InstallOllama();
    end;

    // If Mistral task selected
    if IsTaskSelected('mistral') then
    begin
      if IsOllamaInstalled() then
        DownloadMistral()
      else
      begin
        MsgBox('Ollama is not installed. Please install Ollama first.',
               mbError, MB_OK);
        InstallOllama();
      end;
    end;
  end;
end;
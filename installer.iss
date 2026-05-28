[Setup]
AppName=CS2 Case Tracker
AppVersion=1.0.0
AppPublisher=Refilia
AppPublisherURL=https://github.com/Refilia/CS2_Case-Tracker
DefaultDirName={autopf}\CS2 Case Tracker
DefaultGroupName=CS2 Case Tracker
OutputDir=installer_output
OutputBaseFilename=CS2_Case_Tracker_Setup
SetupIconFile=dist\CS2_tracker.ico
UninstallDisplayIcon={app}\CS2 Case Tracker.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Files]
Source: "dist\CS2 Case Tracker.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\CS2_tracker.ico";      DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\CS2 Case Tracker"; Filename: "{app}\CS2 Case Tracker.exe"; IconFilename: "{app}\CS2_tracker.ico"
Name: "{autodesktop}\CS2 Case Tracker";  Filename: "{app}\CS2 Case Tracker.exe"; IconFilename: "{app}\CS2_tracker.ico"

[Run]
Filename: "{app}\CS2 Case Tracker.exe"; Description: "Launch CS2 Case Tracker"; Flags: nowait postinstall skipifsilent

import 'dart:io';

class FolderPickerException implements Exception {
  final String message;
  FolderPickerException(this.message);

  @override
  String toString() => message;
}

Future<String?> pickFolder({String description = 'Select a folder'}) async {
  final script = '''
Add-Type -AssemblyName System.Windows.Forms
\$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
\$dialog.Description = "$description"
\$dialog.ShowNewFolderButton = \$false
\$result = \$dialog.ShowDialog()
if (\$result -eq [System.Windows.Forms.DialogResult]::OK) {
  Write-Output \$dialog.SelectedPath
  exit 0
} else {
  exit 1
}
''';

  final process = await Process.run(
    'powershell',
    ['-NoProfile', '-STA', '-WindowStyle', 'Hidden', '-Command', script],
  );

  if (process.exitCode == 0) {
    final path = (process.stdout as String).trim();
    return path.isEmpty ? null : path;
  }
  if (process.exitCode == 1) {
    return null;
  }
  throw FolderPickerException('Folder picker failed: ${process.stderr}');
}

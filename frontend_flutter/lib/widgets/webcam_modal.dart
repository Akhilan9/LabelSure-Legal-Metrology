import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../core/theme.dart';

class WebcamModal extends StatefulWidget {
  final void Function(String filename, Uint8List bytes, String panel) onCapture;
  final VoidCallback onClose;

  const WebcamModal({
    super.key,
    required this.onCapture,
    required this.onClose,
  });

  @override
  State<WebcamModal> createState() => _WebcamModalState();
}

class _WebcamModalState extends State<WebcamModal> {
  String _panel = 'FRONT';
  Uint8List? _previewBytes;
  String? _previewName;

  Future<void> _pickFile() async {
    final file = await FilePicker.pickFile(
      type: FileType.image,
    );
    if (file != null) {
      final bytes = await file.readAsBytes();
      setState(() {
        _previewBytes = bytes;
        _previewName = file.name;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(16),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 700),
        decoration: BoxDecoration(
          color: const Color(0xFF0D1527),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.borderSubtle),
          boxShadow: const [
            BoxShadow(color: Colors.black87, blurRadius: 24, offset: Offset(0, 10)),
          ],
        ),
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Package Evidence Scanner',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white, size: 20),
                  onPressed: widget.onClose,
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Viewfinder / Reticle Frame
            Container(
              height: 320,
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF1E293B)),
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  if (_previewBytes != null)
                    Image.memory(_previewBytes!, fit: BoxFit.contain)
                  else
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.camera_alt, size: 48, color: Color(0xFF475569)),
                        const SizedBox(height: 12),
                        const Text(
                          'Align package label inside the guide frame.',
                          style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF1E293B),
                            foregroundColor: Colors.white,
                          ),
                          icon: const Icon(Icons.photo_library, size: 16),
                          label: const Text('Select / Snap Photo', style: TextStyle(fontSize: 11)),
                          onPressed: _pickFile,
                        ),
                      ],
                    ),

                  // Green Alignment Reticle Box
                  Container(
                    margin: const EdgeInsets.all(32),
                    decoration: BoxDecoration(
                      border: Border.all(color: AppTheme.emerald, width: 2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _panel,
                    isDense: true,
                    decoration: const InputDecoration(labelText: 'Package Panel Side'),
                    dropdownColor: const Color(0xFF131D31),
                    style: const TextStyle(fontSize: 12, color: Colors.white),
                    items: const [
                      DropdownMenuItem(value: 'FRONT', child: Text('Front Panel')),
                      DropdownMenuItem(value: 'BACK', child: Text('Back Panel')),
                      DropdownMenuItem(value: 'LEFT', child: Text('Left Side')),
                      DropdownMenuItem(value: 'RIGHT', child: Text('Right Side')),
                      DropdownMenuItem(value: 'MRP_PANEL', child: Text('MRP / Date Panel')),
                      DropdownMenuItem(value: 'DECLARATION_PANEL', child: Text('Statutory Declaration Panel')),
                    ],
                    onChanged: (v) => setState(() => _panel = v ?? 'FRONT'),
                  ),
                ),
                const SizedBox(width: 14),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.emerald,
                    foregroundColor: const Color(0xFF090D16),
                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  icon: const Icon(Icons.check, size: 18),
                  label: const Text('Attach Photo', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  onPressed: _previewBytes != null
                      ? () {
                          widget.onCapture(_previewName ?? 'package.jpg', _previewBytes!, _panel);
                          widget.onClose();
                        }
                      : null,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

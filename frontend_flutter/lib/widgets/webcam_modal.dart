import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../core/theme.dart';

class WebcamModal extends StatefulWidget {
  final void Function(String filename, Uint8List bytes, String panel) onCapture;
  final VoidCallback onClose;

  final String initialPanel;

  const WebcamModal({
    super.key,
    required this.onCapture,
    required this.onClose,
    this.initialPanel = 'FRONT',
  });

  @override
  State<WebcamModal> createState() => _WebcamModalState();
}

class _WebcamModalState extends State<WebcamModal> {
  late String _panel;
  Uint8List? _previewBytes;
  String? _previewName;
  bool _isCapturing = false;
  String? _statusError;

  @override
  void initState() {
    super.initState();
    _panel = widget.initialPanel;
    // Auto-launch device camera on modal open
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _captureFromCamera();
    });
  }

  Future<void> _captureFromCamera() async {
    setState(() {
      _isCapturing = true;
      _statusError = null;
    });

    try {
      final picker = ImagePicker();
      final photo = await picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.rear,
        imageQuality: 92,
      );

      if (photo != null) {
        final bytes = await photo.readAsBytes();
        if (mounted) {
          setState(() {
            _previewBytes = bytes;
            _previewName = photo.name.isNotEmpty ? photo.name : 'camera_photo_${DateTime.now().millisecondsSinceEpoch}.jpg';
            _isCapturing = false;
          });
        }
      } else {
        if (mounted) {
          setState(() => _isCapturing = false);
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCapturing = false;
          _statusError = 'Camera error: $e. You can choose a photo from the gallery instead.';
        });
      }
    }
  }

  Future<void> _pickFromGallery() async {
    setState(() {
      _isCapturing = true;
      _statusError = null;
    });

    try {
      final picker = ImagePicker();
      final photo = await picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 92,
      );

      if (photo != null) {
        final bytes = await photo.readAsBytes();
        if (mounted) {
          setState(() {
            _previewBytes = bytes;
            _previewName = photo.name.isNotEmpty ? photo.name : 'gallery_photo_${DateTime.now().millisecondsSinceEpoch}.jpg';
            _isCapturing = false;
          });
        }
        return;
      }
    } catch (_) {}

    // Fallback to FilePicker if ImagePicker gallery encounters any platform issue
    try {
      final file = await FilePicker.pickFile(type: FileType.image);
      if (file != null) {
        final bytes = await file.readAsBytes();
        if (mounted) {
          setState(() {
            _previewBytes = bytes;
            _previewName = file.name;
            _isCapturing = false;
          });
        }
        return;
      }
    } catch (err) {
      if (mounted) {
        setState(() {
          _statusError = 'Failed to pick photo: $err';
        });
      }
    }

    if (mounted) {
      setState(() => _isCapturing = false);
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
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: const Color(0x3310B981),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Icon(Icons.camera_alt, color: AppTheme.emerald, size: 18),
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      'Package Camera Scanner',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white, size: 20),
                  onPressed: widget.onClose,
                ),
              ],
            ),
            const SizedBox(height: 12),

            if (_statusError != null) ...[
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0x33F43F5E),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.rose),
                ),
                child: Text(
                  _statusError!,
                  style: const TextStyle(fontSize: 11, color: Color(0xFFFECDD3)),
                ),
              ),
              const SizedBox(height: 10),
            ],

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
                    ClipRRect(
                      borderRadius: BorderRadius.circular(11),
                      child: Image.memory(_previewBytes!, fit: BoxFit.contain, width: double.infinity, height: double.infinity),
                    )
                  else if (_isCapturing)
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        CircularProgressIndicator(color: AppTheme.emerald),
                        SizedBox(height: 14),
                        Text('Opening Camera...', style: TextStyle(fontSize: 12, color: Colors.white70)),
                      ],
                    )
                  else
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.camera_alt, size: 52, color: Color(0xFF475569)),
                        const SizedBox(height: 12),
                        const Text(
                          'Align package label inside the camera frame.',
                          style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 10,
                          alignment: WrapAlignment.center,
                          children: [
                            ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppTheme.emerald,
                                foregroundColor: Colors.black,
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                              ),
                              icon: const Icon(Icons.camera, size: 16),
                              label: const Text('📸 Take Photo with Camera', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                              onPressed: _captureFromCamera,
                            ),
                            OutlinedButton.icon(
                              style: OutlinedButton.styleFrom(
                                foregroundColor: Colors.white,
                                side: const BorderSide(color: Color(0xFF334155)),
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                              ),
                              icon: const Icon(Icons.photo_library, size: 16),
                              label: const Text('Choose from Gallery', style: TextStyle(fontSize: 11)),
                              onPressed: _pickFromGallery,
                            ),
                          ],
                        ),
                      ],
                    ),

                  // Alignment Reticle Box
                  IgnorePointer(
                    child: Container(
                      margin: const EdgeInsets.all(28),
                      decoration: BoxDecoration(
                        border: Border.all(color: AppTheme.emerald.withValues(alpha: 0.7), width: 1.5),
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            if (_previewBytes != null) ...[
              Row(
                children: [
                  TextButton.icon(
                    icon: const Icon(Icons.refresh, size: 14, color: AppTheme.emerald),
                    label: const Text('Retake with Camera', style: TextStyle(fontSize: 11, color: AppTheme.emerald)),
                    onPressed: _captureFromCamera,
                  ),
                  const SizedBox(width: 8),
                  TextButton.icon(
                    icon: const Icon(Icons.photo_library, size: 14, color: Color(0xFF94A3B8)),
                    label: const Text('Choose Different Photo', style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                    onPressed: _pickFromGallery,
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],

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

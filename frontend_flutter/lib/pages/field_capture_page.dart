import 'dart:convert';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/api_client.dart';
import '../core/theme.dart';
import '../widgets/webcam_modal.dart';

class OfflineCaseItem {
  final String id;
  final String name;
  final int photoCount;
  String state;
  int uploaded;
  String? error;

  OfflineCaseItem({
    required this.id,
    required this.name,
    required this.photoCount,
    required this.state,
    required this.uploaded,
    this.error,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'photoCount': photoCount,
        'state': state,
        'uploaded': uploaded,
        'error': error,
      };

  factory OfflineCaseItem.fromJson(Map<String, dynamic> json) {
    return OfflineCaseItem(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Field Capture',
      photoCount: json['photoCount'] as int? ?? 0,
      state: json['state']?.toString() ?? 'DRAFT',
      uploaded: json['uploaded'] as int? ?? 0,
      error: json['error']?.toString(),
    );
  }
}

class FieldCapturePage extends StatefulWidget {
  const FieldCapturePage({super.key});

  @override
  State<FieldCapturePage> createState() => _FieldCapturePageState();
}

class _FieldCapturePageState extends State<FieldCapturePage> {
  List<OfflineCaseItem> _items = [];
  final bool _online = true;
  bool _paused = false;
  bool _busy = false;
  bool _cameraOpen = false;

  @override
  void initState() {
    super.initState();
    _loadItems();
  }

  Future<void> _loadItems() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getStringList('labelsure_offline_cases') ?? [];
    setState(() {
      _items = raw.map((str) => OfflineCaseItem.fromJson(jsonDecode(str))).toList();
    });
  }

  Future<void> _saveItems() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = _items.map((i) => jsonEncode(i.toJson())).toList();
    await prefs.setStringList('labelsure_offline_cases', raw);
  }

  void _addCase(String name, int count) {
    final newItem = OfflineCaseItem(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      name: name,
      photoCount: count,
      state: 'DRAFT',
      uploaded: 0,
    );
    setState(() => _items.insert(0, newItem));
    _saveItems();
  }

  Future<void> _queueForSync(OfflineCaseItem item) async {
    setState(() {
      item.state = 'QUEUED';
      _busy = true;
    });

    try {
      final res = await ApiClient().post('/inspections', body: {'product_name': item.name});
      if (res is Map && res['id'] != null) {
        setState(() {
          item.state = 'SYNCED';
          item.uploaded = item.photoCount;
          item.error = null;
        });
      }
    } catch (e) {
      setState(() {
        item.state = 'ERROR';
        item.error = e.toString();
      });
    } finally {
      setState(() => _busy = false);
      _saveItems();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('FIELD WORKSPACE',
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF64748B), letterSpacing: 1)),
        const SizedBox(height: 4),
        const Text('Offline Scanner & Field Capture',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
        const SizedBox(height: 2),
        const Text('Keep package photos on this device, then queue and sync them when connected.',
            style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
        const SizedBox(height: 18),

        // Connectivity & Controls Bar
        Container(
          padding: const EdgeInsets.all(14),
          decoration: AppTheme.glassPanel(),
          child: Row(
            children: [
              Row(
                children: [
                  Icon(_online ? Icons.wifi : Icons.wifi_off, size: 18, color: _online ? AppTheme.emerald : AppTheme.rose),
                  const SizedBox(width: 8),
                  Text(_online ? 'Online / Connected' : 'Offline',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _online ? AppTheme.emerald : AppTheme.rose)),
                ],
              ),
              const SizedBox(width: 24),
              Row(
                children: [
                  Checkbox(
                    value: _paused,
                    activeColor: AppTheme.emerald,
                    onChanged: (v) => setState(() => _paused = v ?? false),
                  ),
                  const Text('Pause automatic sync', style: TextStyle(fontSize: 11, color: Color(0xFFCBD5E1))),
                ],
              ),
              const Spacer(),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.emerald,
                  foregroundColor: const Color(0xFF090D16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: const Icon(Icons.camera_alt, size: 16),
                label: const Text('Open Camera', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                onPressed: () => setState(() => _cameraOpen = true),
              ),
              const SizedBox(width: 8),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Color(0xFF334155)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: const Icon(Icons.photo_library, size: 16),
                label: const Text('Save Local Photos', style: TextStyle(fontSize: 11)),
                onPressed: () async {
                  final files = await FilePicker.pickFiles(type: FileType.image);
                  if (files.isNotEmpty) {
                    _addCase(files.first.name, files.length);
                  }
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),

        if (_cameraOpen)
          WebcamModal(
            onClose: () => setState(() => _cameraOpen = false),
            onCapture: (name, bytes, panel) {
              _addCase(name, 1);
            },
          ),

        // Offline Items List
        if (_items.isEmpty)
          Container(
            padding: const EdgeInsets.all(32),
            decoration: AppTheme.glassPanel(),
            child: const Center(
              child: Text('No photos stored on this device yet.', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
            ),
          )
        else
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final item = _items[index];

              return Container(
                padding: const EdgeInsets.all(16),
                decoration: AppTheme.glassPanel(),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white)),
                          const SizedBox(height: 4),
                          Text('${item.photoCount} photos · State: ${item.state.replaceAll('_', ' ')}',
                              style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                          if (item.error != null) ...[
                            const SizedBox(height: 4),
                            Text(item.error!, style: const TextStyle(fontSize: 10, color: AppTheme.amber)),
                          ],
                        ],
                      ),
                    ),
                    if (item.state == 'DRAFT' || item.state == 'ERROR') ...[
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0x3310B981),
                          foregroundColor: AppTheme.emerald,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                        ),
                        icon: const Icon(Icons.cloud_upload, size: 14),
                        label: Text(item.state == 'ERROR' ? 'Retry Sync' : 'Queue for Sync',
                            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                        onPressed: _busy ? null : () => _queueForSync(item),
                      ),
                      const SizedBox(width: 8),
                    ],
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 18, color: Color(0xFF64748B)),
                      tooltip: 'Remove local copy',
                      onPressed: () {
                        setState(() => _items.removeAt(index));
                        _saveItems();
                      },
                    ),
                  ],
                ),
              );
            },
          ),
      ],
    );
  }
}

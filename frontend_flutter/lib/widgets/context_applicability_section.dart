import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../core/theme.dart';

class ContextApplicabilitySection extends StatefulWidget {
  final Map<String, dynamic> inspection;

  const ContextApplicabilitySection({super.key, required this.inspection});

  @override
  State<ContextApplicabilitySection> createState() => _ContextApplicabilitySectionState();
}

class _ContextApplicabilitySectionState extends State<ContextApplicabilitySection> {
  Map<String, dynamic>? _context;
  bool _loading = false;
  bool _resolving = false;

  String? _packageType;
  String? _productCategory;
  String? _importStatus;
  String? _quantityKind;
  final TextEditingController _originCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final id = widget.inspection['id'];
      final cRes = await ApiClient().get('/inspections/$id/context');
      if (cRes is Map<String, dynamic>) {
        _context = cRes;
      }
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _resolve({bool clear = false}) async {
    setState(() => _resolving = true);
    try {
      final id = widget.inspection['id'];
      final input = clear
          ? {
              'package_type': null,
              'product_category': null,
              'import_status': null,
              'quantity_kind': null,
              'country_of_origin': null,
            }
          : {
              if (_packageType != null && _packageType!.isNotEmpty) 'package_type': _packageType,
              if (_productCategory != null && _productCategory!.isNotEmpty) 'product_category': _productCategory,
              if (_importStatus != null && _importStatus!.isNotEmpty) 'import_status': _importStatus,
              if (_quantityKind != null && _quantityKind!.isNotEmpty) 'quantity_kind': _quantityKind,
              if (_originCtrl.text.trim().isNotEmpty) 'country_of_origin': _originCtrl.text.trim(),
            };

      await ApiClient().post('/inspections/$id/resolve-context', body: {'inspector_input': input});
      await _load();
    } catch (_) {}
    if (mounted) setState(() => _resolving = false);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: AppTheme.glassPanel(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('CONTEXT & APPLICABILITY',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 0.5)),
                    SizedBox(height: 2),
                    Text('Context resolution prepares an inspection for Legal Metrology rule verification.',
                        style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                  ],
                ),
              ),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.emerald,
                  foregroundColor: const Color(0xFF090D16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                icon: _resolving
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Icon(Icons.sync, size: 16),
                label: Text(_resolving ? 'Resolving…' : 'Resolve Context',
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                onPressed: _resolving ? null : () => _resolve(),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Inspector Overrides Expansion Tile
          Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: const Text('Inspector Context Input (Overrides)',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.emerald)),
              subtitle: const Text('Optional inputs are recorded separately from evidence facts.',
                  style: TextStyle(fontSize: 10, color: Color(0xFF64748B))),
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF131D31),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF1E293B)),
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: _buildDropdown(
                              'Package Type',
                              _packageType,
                              ['PACKET', 'BOX', 'BOTTLE', 'JAR', 'CAN', 'POUCH', 'TUBE', 'CARTON', 'OTHER'],
                              (v) => setState(() => _packageType = v),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _buildDropdown(
                              'Product Category',
                              _productCategory,
                              ['FOOD', 'COSMETIC', 'HOUSEHOLD', 'PERSONAL_CARE', 'ELECTRONICS', 'OTHER'],
                              (v) => setState(() => _productCategory = v),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: _buildDropdown(
                              'Import Status',
                              _importStatus,
                              ['DOMESTIC', 'IMPORTED'],
                              (v) => setState(() => _importStatus = v),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _buildDropdown(
                              'Quantity Kind',
                              _quantityKind,
                              ['WEIGHT', 'VOLUME', 'COUNT', 'LENGTH', 'AREA'],
                              (v) => setState(() => _quantityKind = v),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _originCtrl,
                        style: const TextStyle(fontSize: 11, color: Colors.white),
                        decoration: const InputDecoration(
                          labelText: 'Country of Origin',
                          hintText: 'e.g. India',
                          isDense: true,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: () => _resolve(clear: true),
                          child: const Text('Clear saved inputs & re-resolve',
                              style: TextStyle(fontSize: 10, color: AppTheme.amber)),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Resolved Facts Display
          if (_loading)
            const Center(child: CircularProgressIndicator(color: AppTheme.emerald, strokeWidth: 2))
          else if (_context != null && _context!['run'] != null) ...[
            const Text('Product & Package Context Facts',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: ['PRODUCT_CATEGORY', 'PACKAGE_TYPE', 'IMPORT_STATUS', 'COUNTRY_OF_ORIGIN', 'QUANTITY_KIND'].map((key) {
                final resolvedMap = _context!['resolved'] as Map<String, dynamic>?;
                final fact = resolvedMap?[key] as Map<String, dynamic>?;
                final val = fact?['value']?.toString() ?? 'Unknown';
                final state = fact?['state']?.toString() ?? 'NORMAL';
                final isConflict = state == 'CONFLICTING' || state == 'REVIEW_REQUIRED';

                return Container(
                  width: 180,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: isConflict ? const Color(0x33F59E0B) : const Color(0xFF131D31),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: isConflict ? AppTheme.amber : const Color(0xFF1E293B),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(key.replaceAll('_', ' '),
                          style: const TextStyle(fontSize: 9, color: Color(0xFF64748B), fontWeight: FontWeight.bold)),
                      const SizedBox(height: 3),
                      Text(val.replaceAll('_', ' '),
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
                      Text(state, style: TextStyle(fontSize: 9, color: isConflict ? AppTheme.amber : AppTheme.emerald)),
                    ],
                  ),
                );
              }).toList(),
            ),
          ] else
            const Text('No current context snapshot. Click "Resolve Context" to prepare applicability.',
                style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
        ],
      ),
    );
  }

  Widget _buildDropdown(String label, String? value, List<String> options, ValueChanged<String?> onChanged) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      isDense: true,
      decoration: InputDecoration(labelText: label, isDense: true),
      dropdownColor: const Color(0xFF131D31),
      style: const TextStyle(fontSize: 11, color: Colors.white),
      items: [
        const DropdownMenuItem(value: '', child: Text('Keep metadata / default')),
        ...options.map((opt) => DropdownMenuItem(value: opt, child: Text(opt.replaceAll('_', ' ')))),
      ],
      onChanged: onChanged,
    );
  }
}

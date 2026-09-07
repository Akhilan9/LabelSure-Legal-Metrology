import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/theme.dart';

class ComingSoonPage extends StatelessWidget {
  final String title;
  final bool forbidden;

  const ComingSoonPage({
    super.key,
    this.title = 'Page Under Development',
    this.forbidden = false,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 450),
        padding: const EdgeInsets.all(32),
        decoration: AppTheme.glassPanel(),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              forbidden ? Icons.lock_outline : Icons.construction_outlined,
              size: 48,
              color: forbidden ? AppTheme.rose : AppTheme.amber,
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              forbidden
                  ? 'Your account role does not have statutory clearance to access this module.'
                  : 'This functionality is being prepared in subsequent statutory enforcement phases.',
              style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8), height: 1.5),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.emerald),
              onPressed: () => context.go('/dashboard'),
              child: const Text('Return to Dashboard', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }
}

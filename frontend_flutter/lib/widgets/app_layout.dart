import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../core/auth_state.dart';
import '../core/theme.dart';

class NavItem {
  final String path;
  final String label;
  final String iconEmoji;

  const NavItem(this.path, this.label, this.iconEmoji);
}

const navItems = [
  NavItem('/dashboard', 'Dashboard', '📊'),
  NavItem('/inspection-center', 'Inspection Center', '🏢'),
  NavItem('/inspections/new', 'New Inspection', '➕'),
  NavItem('/inspections', 'Inspections Repository', '📁'),
  NavItem('/reports', 'Compliance Reports', '📑'),
  NavItem('/field', 'Offline Scanner', '📷'),
  NavItem('/rules', 'Rule Repository', '📜'),
];

class AppLayout extends StatefulWidget {
  final Widget child;

  const AppLayout({super.key, required this.child});

  @override
  State<AppLayout> createState() => _AppLayoutState();
}

class _AppLayoutState extends State<AppLayout> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  Widget build(BuildContext context) {
    final currentPath = GoRouterState.of(context).uri.path;
    final isDesktop = MediaQuery.of(context).size.width >= 1024;
    final auth = context.watch<AuthProvider>();
    final user = auth.user;

    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: AppTheme.bgPrimary,
      drawer: isDesktop ? null : Drawer(
        backgroundColor: const Color(0xFF070B14),
        child: _buildSidebarContent(currentPath, user, isDrawer: true),
      ),
      body: Row(
        children: [
          // Desktop Fixed Sidebar
          if (isDesktop)
            Container(
              width: 270,
              decoration: const BoxDecoration(
                color: Color(0xFF070B14),
                border: Border(right: BorderSide(color: Color(0xFF1E293B))),
              ),
              child: _buildSidebarContent(currentPath, user, isDrawer: false),
            ),

          // Main Canvas
          Expanded(
            child: Column(
              children: [
                // Top Header Bar
                Container(
                  height: 60,
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  decoration: const BoxDecoration(
                    color: Color(0xD9090D16),
                    border: Border(bottom: BorderSide(color: Color(0xFF1E293B))),
                  ),
                  child: Row(
                    children: [
                      if (!isDesktop) ...[
                        IconButton(
                          icon: const Icon(Icons.menu, color: Colors.white, size: 22),
                          onPressed: () => _scaffoldKey.currentState?.openDrawer(),
                        ),
                        const SizedBox(width: 8),
                      ],
                      const Text(
                        'OFFICIAL INSPECTION SYSTEM',
                        style: TextStyle(
                          fontSize: 11,
                          fontFamily: 'monospace',
                          color: Color(0xFF94A3B8),
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text('•', style: TextStyle(color: Color(0xFF475569))),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0x3310B981),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: const Color(0x4D10B981)),
                        ),
                        child: const Text(
                          'LMPC RULES 2011–2026 ENFORCEMENT',
                          style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.emerald),
                        ),
                      ),
                      const Spacer(),
                      // Online pill
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFF334155)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 7,
                              height: 7,
                              decoration: const BoxDecoration(
                                color: AppTheme.emerald,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            const Text(
                              'FastAPI & OpenCV Engine Online',
                              style: TextStyle(fontSize: 11, color: Color(0xFFCBD5E1), fontFamily: 'monospace'),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

                // Page Outlet Area
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(24),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1300),
                        child: widget.child,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSidebarContent(String currentPath, User? user, {required bool isDrawer}) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Logo & Brand Seal
          InkWell(
            onTap: () => context.go('/dashboard'),
            child: Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF059669), Color(0xFF06B6D4)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(10),
                    boxShadow: const [
                      BoxShadow(color: Color(0x4010B981), blurRadius: 10, offset: Offset(0, 3)),
                    ],
                  ),
                  child: const Center(
                    child: Text('L✓', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
                  ),
                ),
                const SizedBox(width: 10),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'LabelSure',
                          style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                          decoration: BoxDecoration(
                            color: const Color(0x3310B981),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: const Color(0x6610B981)),
                          ),
                          child: const Text('APEX', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppTheme.emerald)),
                        ),
                      ],
                    ),
                    const Text('LEGAL METROLOGY AI', style: TextStyle(fontSize: 9, fontFamily: 'monospace', color: Color(0xFF64748B), letterSpacing: 0.8)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 28),

          const Text(
            'INSPECTION PLATFORM',
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF475569), letterSpacing: 1),
          ),
          const SizedBox(height: 12),

          // Nav Items
          ...navItems.map((item) {
            final active = currentPath == item.path ||
                (item.path != '/dashboard' && currentPath.startsWith(item.path));

            return Container(
              margin: const EdgeInsets.only(bottom: 6),
              child: InkWell(
                onTap: () {
                  if (isDrawer) Navigator.of(context).pop();
                  context.go(item.path);
                },
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                  decoration: BoxDecoration(
                    color: active ? const Color(0x2610B981) : Colors.transparent,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: active ? const Color(0x4D10B981) : Colors.transparent,
                    ),
                  ),
                  child: Row(
                    children: [
                      Text(item.iconEmoji, style: const TextStyle(fontSize: 15)),
                      const SizedBox(width: 12),
                      Text(
                        item.label,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: active ? FontWeight.bold : FontWeight.w500,
                          color: active ? AppTheme.emerald : const Color(0xFF94A3B8),
                        ),
                      ),
                      if (active) ...[
                        const Spacer(),
                        Container(
                          width: 5,
                          height: 5,
                          decoration: const BoxDecoration(
                            color: AppTheme.emerald,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            );
          }),

          const Spacer(),

          // User Profile Pill & Sign Out
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF1E293B)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: const BoxDecoration(color: AppTheme.emerald, shape: BoxShape.circle),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            user?.role ?? 'INSPECTOR',
                            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.emerald, fontFamily: 'monospace'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 3),
                      Text(
                        user?.fullName ?? 'Legal Officer',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        user?.email ?? 'officer@labelsure.local',
                        style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.logout, size: 18, color: Color(0xFF94A3B8)),
                  tooltip: 'Sign Out',
                  onPressed: () async {
                    final router = GoRouter.of(context);
                    await context.read<AuthProvider>().logout();
                    router.go('/login');
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

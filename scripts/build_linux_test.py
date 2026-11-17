from pathlib import Path
import unittest

from build_linux import system_link_command


class CrossLinkTests(unittest.TestCase):
    def test_current_compiler_prefix_and_relative_stub_object_are_handled(self):
        log = ('  > cc -c -o linux_cross_0.o src.c\n'
               '  > cc -c -o linux_cross_1.o /v/thirdparty/pg/pgport_stubs.c\n'
               '  > /sysroot/ld.lld -o out linux_cross_0.o linux_cross_1.o -lpq -lc\n')
        self.assertEqual(system_link_command(log, Path('/system/libpq.so.5'), Path('/release/site')),
                         ['/sysroot/ld.lld', '-o', '/release/site', 'linux_cross_0.o',
                          '/system/libpq.so.5', '-lc', '--allow-shlib-undefined'])

    def test_legacy_absolute_stub_is_removed_and_paths_with_spaces_are_preserved(self):
        log = '"/sys root/ld.lld" -o "/old output" /tmp/site.o /tmp/pgport_stubs.c.o -lpq -lc'
        command = system_link_command(log, Path('/system path/libpq.so.5'), Path('/new output'))
        self.assertEqual(command, ['/sys root/ld.lld', '-o', '/new output', '/tmp/site.o',
                                   '/system path/libpq.so.5', '-lc', '--allow-shlib-undefined'])

    def test_missing_link_command_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Could not locate'):
            system_link_command('compiler failed', Path('/libpq'), Path('/site'))


if __name__ == '__main__':
    unittest.main()

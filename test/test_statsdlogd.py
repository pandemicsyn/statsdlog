from mock import patch, Mock, MagicMock, sentinel, call
from statsdlog.statsdlogd import StatsdLog
import unittest

class testit(unittest.TestCase):

    def setUp(self):
        self.sdl = self._sdl_init()

    @patch('__builtin__.open')
    def _sdl_init(self, open_mock):
        file_contents = '{"one": "something.*"}'
        file_path = '/etc/statsdlog/patterns.json'
        context_manager_mock = Mock()
        open_mock.return_value = context_manager_mock
        file_mock = Mock()
        file_mock.read.return_value = file_contents
        enter_mock = Mock()
        enter_mock.return_value = file_mock
        exit_mock  = Mock()
        setattr( context_manager_mock, '__enter__', enter_mock )
        setattr( context_manager_mock, '__exit__', exit_mock )
        result = StatsdLog(conf={'debug': 'y'})
        self.assertEquals(open_mock.call_args, call(file_path))
        self.assertEquals(result.patterns, {'one': 'something.*'})
        return result

    def test_check_line(self):
        self.assertEquals(self.sdl.check_line('no matches'), None)
        self.assertEquals(self.sdl.check_line('something matches'), 'one')

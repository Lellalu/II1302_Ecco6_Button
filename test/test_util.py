from ecco6 import util


def test_create_memory_file():
  content = b'hello world'
  filename = "foo"
  memory_file = util.create_memory_file(content, filename)
  assert memory_file.getbuffer() == content
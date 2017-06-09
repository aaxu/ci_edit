# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Key bindings for the ciEditor."""

from app.curses_util import *
import app.buffer_manager
import app.controller
import curses
import curses.ascii
import os
import re
import subprocess
import text_buffer


def functionTestEq(a, b):
  assert a == b, "%r != %r"%(a, b)

if 1:
  # Break up a command line, separate by |.
  kRePipeChain = re.compile(
      #r'''\|\|?|&&|((?:"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s|&]+)+)''')
      r'''((?:"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|\|\||[^|]+)+)''')
  functionTestEq(kRePipeChain.findall(''' date "a b" 'c d ' | sort '''),
      [""" date "a b" 'c d ' """, ' sort '])
  functionTestEq(kRePipeChain.findall('date'),
      ['date'])
  functionTestEq(kRePipeChain.findall('d-a.te'),
      ['d-a.te'])
  functionTestEq(kRePipeChain.findall('date | wc'),
      ['date ', ' wc'])
  functionTestEq(kRePipeChain.findall('date|wc'),
      ['date', 'wc'])
  functionTestEq(kRePipeChain.findall('date && sort'),
      ['date && sort'])
  functionTestEq(kRePipeChain.findall('date || sort'),
      ['date || sort'])
  functionTestEq(kRePipeChain.findall('''date "a b" 'c d ' || sort'''),
      ["""date "a b" 'c d ' || sort"""])


# Break up a command line, separate by &&.
kReLogicChain = re.compile(
    r'''\s*(\|\|?|&&|"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s|&]+)''')
functionTestEq(kReLogicChain.findall('date'),
    ['date'])
functionTestEq(kReLogicChain.findall('d-a.te'),
    ['d-a.te'])
functionTestEq(kReLogicChain.findall('date | wc'),
    ['date', '|', 'wc'])
functionTestEq(kReLogicChain.findall('date|wc'),
    ['date', '|', 'wc'])
functionTestEq(kReLogicChain.findall('date && sort'),
    ['date', '&&', 'sort'])
functionTestEq(kReLogicChain.findall('date || sort'),
    ['date', '||', 'sort'])
functionTestEq(kReLogicChain.findall(''' date "a\\" b" 'c d ' || sort '''),
    ['date', '"a\\" b"', "'c d '", '||', 'sort'])


# Break up a command line, separate by \\s.
kReArgChain = re.compile(
    r'''\s*("(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s]+)''')
functionTestEq(kReArgChain.findall('date'),
    ['date'])
functionTestEq(kReArgChain.findall('d-a.te'),
    ['d-a.te'])
functionTestEq(kReArgChain.findall(
    ''' date "a b" 'c d ' "a\\" b" 'c\\' d ' '''),
    ['date', '"a b"', "'c d '", '"a\\" b"', "'c\\' d '"])
functionTestEq(kReArgChain.findall(
    '''bm +'''),
    ['bm', '+'])


# Break up a command line, separate by \w (non-word chars will be separated).
kReSplitCmdLine = re.compile(
    r"""\s*("(?:\\"|[^"])*"|'(?:\\'|[^'])*'|\w+|[^\s]+)\s*""")
functionTestEq(kReSplitCmdLine.findall(
    '''bm ab'''),
    ['bm', 'ab'])
functionTestEq(kReSplitCmdLine.findall(
    '''bm+'''),
    ['bm', '+'])
functionTestEq(kReSplitCmdLine.findall(
    '''bm "one two"'''),
    ['bm', '"one two"'])
functionTestEq(kReSplitCmdLine.findall(
    '''bm "o\\"ne two"'''),
    ['bm', '"o\\"ne two"'])


# Unquote text.
kReUnquote = re.compile(r'''(["'])([^\1]*)\1''')
functionTestEq(kReUnquote.sub('\\2', 'date'),
    'date')
functionTestEq(kReUnquote.sub('\\2', '"date"'),
    'date')
functionTestEq(kReUnquote.sub('\\2', "'date'"),
    'date')
functionTestEq(kReUnquote.sub('\\2', "'da\\'te'"),
    "da\\'te")
functionTestEq(kReUnquote.sub('\\2', '"da\\"te"'),
    'da\\"te')


def parseInt(str):
  i = 0
  k = 0
  if len(str) > i and str[i] in ('+', '-'):
    i += 1
  k = i
  while len(str) > k and str[k].isdigit():
    k += 1
  if k > i:
    return int(str[:k])
  return 0

def test_parseInt():
  assert parseInt('0') == 0
  assert parseInt('0e') == 0
  assert parseInt('qwee') == 0
  assert parseInt('10') == 10
  assert parseInt('+10') == 10
  assert parseInt('-10') == -10
  assert parseInt('--10') == 0
  assert parseInt('--10') == 0


class InteractiveOpener(app.controller.Controller):
  """Open a file to edit."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'opener')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def createOrOpen(self):
    self.changeToHostWindow()

  def focus(self):
    app.log.info('InteractiveOpener.focus\n',
        self.host.textBuffer.fullPath)
    self.priorTextBuffer = self.host.textBuffer
    self.commandDefault = self.textBuffer.insertPrintable
    self.textBuffer.selectionAll()
    self.textBuffer.editPasteLines((self.host.textBuffer.fullPath,))
    # Create a new text buffer to display dir listing.
    self.host.setTextBuffer(text_buffer.TextBuffer())

  def info(self):
    app.log.info('InteractiveOpener command set')

  def maybeSlash(self, expandedPath):
    if (self.textBuffer.lines[0] and self.textBuffer.lines[0][-1] != '/' and
        os.path.isdir(expandedPath)):
      self.textBuffer.insert('/')

  def tabCompleteFirst(self):
    """Find the first file that starts with the pattern."""
    dirPath, fileName = os.path.split(self.lines[0])
    foundOnce = ''
    app.log.debug('tabComplete\n', dirPath, '\n', fileName)
    for i in os.listdir(os.path.expandvars(os.path.expanduser(dirPath)) or '.'):
      if i.startswith(fileName):
        if foundOnce:
          # Found more than one match.
          return
        fileName = os.path.join(dirPath, i)
        if os.path.isdir(fileName):
          fileName += '/'
        self.lines[0] = fileName
        self.onChange()
        return

  def tabCompleteExtend(self):
    """Extend the selection to match characters in common."""
    dirPath, fileName = os.path.split(self.textBuffer.lines[0])
    expandedDir = os.path.expandvars(os.path.expanduser(dirPath)) or '.'
    matches = []
    if not os.path.isdir(expandedDir):
      return
    for i in os.listdir(expandedDir):
      if i.startswith(fileName):
        matches.append(i)
      else:
        pass
        #app.log.info('not', i)
    if len(matches) <= 0:
      self.maybeSlash(expandedDir)
      self.onChange()
      return
    if len(matches) == 1:
      self.textBuffer.insert(matches[0][len(fileName):])
      self.maybeSlash(os.path.join(expandedDir, matches[0]))
      self.onChange()
      return
    def findCommonPrefixLength(prefixLen):
      count = 0
      ch = None
      for match in matches:
        if len(match) <= prefixLen:
          return prefixLen
        if not ch:
          ch = match[prefixLen]
        if match[prefixLen] == ch:
          count += 1
      if count and count == len(matches):
        return findCommonPrefixLength(prefixLen + 1)
      return prefixLen
    prefixLen = findCommonPrefixLength(len(fileName))
    self.textBuffer.insert(matches[0][len(fileName):prefixLen])
    self.onChange()

  def oldAutoOpenOnChange(self):
    path = os.path.expanduser(os.path.expandvars(self.textBuffer.lines[0]))
    dirPath, fileName = os.path.split(path)
    dirPath = dirPath or '.'
    app.log.info('O.onChange', dirPath, fileName)
    if os.path.isdir(dirPath):
      lines = []
      for i in os.listdir(dirPath):
        if i.startswith(fileName):
          lines.append(i)
      if len(lines) == 1 and os.path.isfile(os.path.join(dirPath, fileName)):
        self.host.setTextBuffer(app.buffer_manager.buffers.loadTextBuffer(
            os.path.join(dirPath, fileName)))
      else:
        self.host.textBuffer.lines = [
            os.path.abspath(os.path.expanduser(dirPath))+":"] + lines
    else:
      self.host.textBuffer.lines = [
          os.path.abspath(os.path.expanduser(dirPath))+": not found"]

  def onChange(self):
    input = self.textBuffer.lines[0]
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(input)))
    dirPath = path or '.'
    fileName = ''
    if len(input) > 0 and input[-1] != os.sep:
      dirPath, fileName = os.path.split(path)
    app.log.info('\n\nO.onChange\n', path, '\n', dirPath, fileName)
    if os.path.isdir(dirPath):
      lines = []
      for i in os.listdir(dirPath):
        if os.path.isdir(i):
          i += '/'
        lines.append(i)
      clip = [dirPath+":"] + lines
    else:
      clip = [dirPath+": not found"]
    app.log.info(clip)
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.editPasteLines(tuple(clip))
    self.host.textBuffer.findPlainText(fileName)

  def unfocus(self):
    expandedPath = os.path.abspath(os.path.expanduser(self.textBuffer.lines[0]))
    if os.path.isdir(expandedPath):
      app.log.info('dir\n\n', expandedPath)
      self.host.setTextBuffer(
          app.buffer_manager.buffers.getValidTextBuffer(self.priorTextBuffer))
    else:
      app.log.info('non-dir\n\n', expandedPath)
      app.log.info('non-dir\n\n',
          app.buffer_manager.buffers.loadTextBuffer(expandedPath).lines[0])
      self.host.setTextBuffer(
          app.buffer_manager.buffers.loadTextBuffer(expandedPath))


class InteractivePrediction(app.controller.Controller):
  """Make a guess about what the user desires."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'opener')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def cancel(self):
    self.items = [(self.priorTextBuffer, '')]
    self.index = 0
    self.changeToHostWindow()

  def cursorMoveTo(self, row, col):
    textBuffer = self.document.textBuffer
    textBuffer.cursorMoveTo(row, col)
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def focus(self):
    app.log.info('InteractivePrediction.focus')
    self.commandDefault = self.textBuffer.insertPrintable
    self.priorTextBuffer = self.host.textBuffer
    self.index = self.buildFileList(self.host.textBuffer.fullPath)
    self.host.setTextBuffer(text_buffer.TextBuffer())
    self.host.textBuffer.rootGrammar = app.prefs.getGrammar('_pre')

  def info(self):
    app.log.info('InteractivePrediction command set')

  def buildFileList(self, currentFile):
    self.items = []
    for i in app.buffer_manager.buffers.buffers:
      dirty = '*' if i.isDirty() else '.'
      if i.fullPath:
        self.items.append((i, i.fullPath, dirty))
      else:
        self.items.append((i, '<new file> %s'%(i.lines[0][:20]), dirty))
    dirPath, fileName = os.path.split(currentFile)
    file, ext = os.path.splitext(fileName)
    # TODO(dschuyler): rework this ignore list.
    ignoreExt = set(('.pyc', '.pyo', '.o', '.obj', '.tgz', '.zip', '.tar',))
    for i in os.listdir(os.path.expandvars(os.path.expanduser(dirPath)) or '.'):
      f, e = os.path.splitext(i)
      if file == f and ext != e and e not in ignoreExt:
        self.items.append((None, os.path.join(dirPath, i), ' '))
    # Suggest item.
    return (len(app.buffer_manager.buffers.buffers) - 2) % len(self.items)

  def onChange(self):
    input = self.textBuffer.lines[0]
    clip = []
    limit = max(5, self.host.cols-10)
    for i,item in enumerate(self.items):
      prefix = '-->' if i == self.index else '   '
      suffix = ' <--' if i == self.index else ''
      clip.append("%s %s %s%s"%(prefix, item[1][-limit:], item[2], suffix))
    app.log.info(clip)
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.editPasteLines(tuple(clip))
    self.cursorMoveTo(self.index, 0)

  def nextItem(self):
    self.index = (self.index + 1) % len(self.items)

  def priorItem(self):
    self.index = (self.index - 1) % len(self.items)

  def selectItem(self):
    self.changeToHostWindow()

  def unfocus(self):
    textBuffer, fullPath = self.items[self.index][:2]
    if textBuffer is not None:
      self.host.setTextBuffer(
          app.buffer_manager.buffers.getValidTextBuffer(textBuffer))
    else:
      expandedPath = os.path.abspath(os.path.expanduser(fullPath))
      self.host.setTextBuffer(
          app.buffer_manager.buffers.loadTextBuffer(expandedPath))
    self.items = None


class InteractiveFind(app.controller.Controller):
  """Find text within the current document."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'find')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def findNext(self):
    self.findCmd = self.document.textBuffer.findNext

  def findPrior(self):
    self.findCmd = self.document.textBuffer.findPrior

  def findReplace(self):
    self.findCmd = self.document.textBuffer.findReplace

  def focus(self):
    app.log.info('InteractiveFind')
    self.findCmd = self.document.textBuffer.find
    selection = self.document.textBuffer.getSelectedText()
    if selection:
      self.textBuffer.selectionAll()
      # Make a single regex line.
      selection = "\\n".join(selection)
      app.log.info(selection)
      self.textBuffer.insert(selection)
    self.textBuffer.selectionAll()

  def info(self):
    app.log.info('InteractiveFind command set')

  def onChange(self):
    app.log.info('InteractiveFind')
    searchFor = self.textBuffer.lines[0]
    try:
      self.findCmd(searchFor)
    except re.error, e:
      self.error = e.message
    self.findCmd = self.document.textBuffer.find


class InteractiveGoto(app.controller.Controller):
  """Jump to a particular line number."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'goto')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def focus(self):
    app.log.info('InteractiveGoto.focus')
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(self.document.textBuffer.cursorRow+1))
    self.textBuffer.selectionAll()

  def info(self):
    app.log.info('InteractiveGoto command set')

  def gotoBottom(self):
    app.log.info()
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(len(self.document.textBuffer.lines)))
    self.changeToHostWindow()

  def gotoHalfway(self):
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(len(self.document.textBuffer.lines)/2+1))
    self.changeToHostWindow()

  def gotoTop(self):
    app.log.info(self.document)
    self.textBuffer.selectionAll()
    self.textBuffer.insert("0")
    self.changeToHostWindow()

  def cursorMoveTo(self, row, col):
    textBuffer = self.document.textBuffer
    textBuffer.cursorMoveTo(row, col)
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def onChange(self):
    app.log.info()
    line = ''
    try: line = self.textBuffer.lines[0]
    except: pass
    gotoLine, gotoCol = (line.split(',') + ['0', '0'])[:2]
    self.cursorMoveTo(parseInt(gotoLine)-1, parseInt(gotoCol))


class InteractivePrompt(app.controller.Controller):
  """Extended commands prompt."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'prompt')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]
    self.commands = {
      'bm': self.bookmarkCommand,
      'build': self.buildCommand,
      'make': self.makeCommand,
    }
    self.filters = {
      'format': self.formatCommand,
      'lower': self.lowerSelectedLines,
      's' : self.substituteText,
      'sort': self.sortSelectedLines,
      'sub' : self.substituteText,
      'upper': self.upperSelectedLines,
    }
    self.subExecute = {
      '!': self.shellExecute,
      '|': self.pipeExecute,
    }

  def bookmarkCommand(self, cmdLine, view):
    args = kReSplitCmdLine.findall(cmdLine)
    if len(args) > 1 and args[1][0] == '-':
      if self.host.textBuffer.bookmarkRemove():
        return {}, 'Removed bookmark'
      else:
        return {}, 'No bookmarks'
    else:
      self.host.textBuffer.bookmarkAdd()
      return {}, 'Added bookmark'

  def buildCommand(self, cmdLine, view):
    return {}, 'building things'

  def focus(self):
    app.log.info('InteractivePrompt.focus')
    self.textBuffer.selectionAll()

  def formatCommand(self, cmdLine, lines):
    formatter = {
      #".js": app.format_javascript.format
      #".py": app.format_python.format
      #".html": app.format_html.format,
    }
    def noOp(data):
      return data
    file, ext = os.path.splitext(self.host.textBuffer.fullPath)
    app.log.info(file, ext)
    lines = self.host.textBuffer.doDataToLines(
        formatter.get(ext, noOp)(self.host.textBuffer.doLinesToData(lines)))
    return lines, 'Changed %d lines'%(len(lines),)

  def makeCommand(self, cmdLine, view):
    return {}, 'making stuff'

  def execute(self):
    try:
      cmdLine = ''
      try: cmdLine = self.textBuffer.lines[0]
      except: pass
      if not len(cmdLine):
        return
      tb = self.host.textBuffer
      lines = list(tb.getSelectedText())
      if cmdLine[0] in self.subExecute:
        data = self.host.textBuffer.doLinesToData(lines)
        output, message = self.subExecute.get(cmdLine[0])(
            cmdLine[1:], data)
        output = tb.doDataToLines(output)
        if tb.selectionMode == app.selectable.kSelectionLine:
          output.append('')
        tb.editPasteLines(tuple(output))
        tb.setMessage(message)
      else:
        cmd = re.split('\\W', cmdLine)[0]
        filter = self.filters.get(cmd)
        if filter:
          if not len(lines):
            tb.setMessage('The %s filter needs a selection.'%(cmd,))
          else:
            lines, message = filter(cmdLine, lines)
            tb.setMessage(message)
            if not len(lines):
              lines.append('')
            if tb.selectionMode == app.selectable.kSelectionLine:
              lines.append('')
            tb.editPasteLines(tuple(lines))
        else:
          command = self.commands.get(cmd, self.unknownCommand)
          results, message = command(cmdLine, self.host)
          tb.setMessage(message)
    except:
      tb.setMessage('Execution threw an error.')
    self.changeToHostWindow()

  def shellExecute(self, commands, input):
    try:
      process = subprocess.Popen(commands,
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT, shell=True);
      return process.communicate(input)[0], ''
    except Exception, e:
      return '', 'Error running shell command\n' + e

  def pipeExecute(self, commands, input):
    chain = kRePipeChain.findall(commands)
    app.log.info('chain', chain)
    try:
      app.log.info(kReArgChain.findall(chain[-1]))
      process = subprocess.Popen(kReArgChain.findall(chain[-1]),
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT);
      if len(chain) == 1:
        return process.communicate(input)[0], ''
      else:
        chain.reverse()
        prior = process
        for i in chain[1:]:
          app.log.info(kReArgChain.findall(i))
          prior = subprocess.Popen(kReArgChain.findall(i),
              stdin=subprocess.PIPE, stdout=prior.stdin,
              stderr=subprocess.STDOUT);
        prior.communicate(input)
        return process.communicate()[0], ''
    except Exception, e:
      return '', 'Error running shell command\n' + e

  def info(self):
    app.log.info('InteractivePrompt command set')

  def lowerSelectedLines(self, cmdLine, lines):
    lines = [line.lower() for line in lines]
    return lines, 'Changed %d lines'%(len(lines),)

  def sortSelectedLines(self, cmdLine, lines):
    lines.sort()
    return lines, 'Changed %d lines'%(len(lines),)

  def substituteText(self, cmdLine, lines):
    if len(cmdLine) < 2:
      return lines, '''tip: %s/foo/bar/ to replace 'foo' with 'bar'.''' % (
          cmdLine,)
    if not lines:
      return lines, 'No text was selected.'
    sre = re.match('\w+(\W)', cmdLine)
    if not sre:
      return lines, '''Separator punctuation missing, example:''' \
          ''' %s/foo/bar/''' % (cmdLine,)
    separator = sre.groups()[0]
    try:
      a, find, replace, flags = cmdLine.split(separator, 3)
    except:
      return lines, '''Separator punctuation missing, there should be''' \
          ''' three '%s'.''' % (separator,)
    data = self.host.textBuffer.doLinesToData(lines)
    output = self.host.textBuffer.findReplaceText(find, replace, flags, data)
    lines = self.host.textBuffer.doDataToLines(output)
    return lines, 'Changed %d lines'%(len(lines),)

  def upperSelectedLines(self, cmdLine, lines):
    lines = [line.upper() for line in lines]
    return lines, 'Changed %d lines'%(len(lines),)

  def unknownCommand(self, cmdLine, view):
    self.host.textBuffer.setMessage('Unknown command')
    return {}, 'Unknown command %s' % (cmdLine,)

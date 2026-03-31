import re
from pathlib import Path

# 1
p = Path('realize_core/media/__init__.py')
if p.exists():
    p.write_text(re.sub(r'^from pathlib import Path\n', '', p.read_text('utf-8', errors='ignore'), flags=re.MULTILINE), 'utf-8')

# 2
p = Path('realize_core/security/__init__.py')
if p.exists():
    p.write_text(re.sub(r'^import hashlib\n', '', p.read_text('utf-8', errors='ignore'), flags=re.MULTILINE), 'utf-8')

# 3
p = Path('realize_core/workflows/__init__.py')
if p.exists():
    text = p.read_text('utf-8', errors='ignore')
    text = re.sub(r'from collections\.abc import Callable, Coroutine', 'from collections.abc import Callable', text)
    text = re.sub(r' *model = node\.config\.get\("model", ""\)\n', '', text)
    p.write_text(text, 'utf-8')

# 4
p = Path('tests/test_registry.py')
if p.exists():
    text = p.read_text('utf-8', errors='ignore')
    text = text.replace(' MockClaude:', ' mock_claude_cls:')
    text = text.replace('MockClaude.return_value', 'mock_claude_cls.return_value')
    text = text.replace(' MockGemini:', ' mock_gemini_cls:')
    text = text.replace('MockGemini.return_value', 'mock_gemini_cls.return_value')
    p.write_text(text, 'utf-8')

# 5
p = Path('tests/test_scaffold.py')
if p.exists():
    text = p.read_text('utf-8', errors='ignore')
    text = re.sub(r' *stats = scaffold_dev_process', '        scaffold_dev_process', text)
    text = re.sub(r' *stats1 = scaffold_dev_process', '        scaffold_dev_process', text)
    p.write_text(text, 'utf-8')

# 6
p = Path('tests/test_skill_executor.py')
if p.exists():
    text = p.read_text('utf-8', errors='ignore')
    text = re.sub(r' *result = await execute_skill', '            await execute_skill', text)
    p.write_text(text, 'utf-8')

import io
with io.open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with io.open('main.py', 'w', encoding='utf-8') as f:
    for i, line in enumerate(lines):
        if 279 <= i <= 336:  # lines 280 to 337 (0-indexed 279 to 336)
            f.write('    ' + line)
        else:
            f.write(line)
print("Indentation fixed.")

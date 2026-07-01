import re

translated_stderr = "Anti-Abuse Rule triggered! at /tmp/layer7_jvd5i8xk.pl line 75."
preamble_len = 47
start_line = 71

def replacer_word(match):
    line_no = int(match.group(1))
    print(f"Matched! {line_no}")
    if line_no > preamble_len:
        return f"line {line_no - preamble_len + start_line}"
    return match.group(0)

print(re.sub(r'line\s+(\d+)', replacer_word, translated_stderr))

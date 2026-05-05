import streamlit as st
import streamlit.components.v1 as components
import json

report_content = "## 这是一个测试报告\n包含引号 ' 和双引号 \" \n而且还有反斜杠 \\"

safe_content = json.dumps(report_content)

copy_html = f"""
<style>
body {{ margin: 0; padding: 0; background: transparent; }}
.btn {{ background: #000; color: #00ff88; padding: 10px; border: 1px solid #00ff88; cursor: pointer; width: 100%; }}
</style>
<button id="mybtn" class="btn">COPY TO CLIPBOARD</button>
<script>
    const content = {safe_content};
    const btn = document.getElementById("mybtn");
    btn.onclick = function() {{
        navigator.clipboard.writeText(content).then(() => {{
            btn.innerText = "COPIED!";
            setTimeout(() => btn.innerText = "COPY TO CLIPBOARD", 2000);
        }}).catch(err => {{
            const textArea = document.createElement("textarea");
            textArea.value = content;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand("copy");
            document.body.removeChild(textArea);
            btn.innerText = "COPIED! (FALLBACK)";
            setTimeout(() => btn.innerText = "COPY TO CLIPBOARD", 2000);
        }});
    }};
</script>
"""

st.write("Below is the component:")
components.html(copy_html, height=50)

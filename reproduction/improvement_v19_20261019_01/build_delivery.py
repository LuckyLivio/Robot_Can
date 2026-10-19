"""Rebuild report artifacts and apply the final root-navigation README contract.

Keep the original plotting source byte-identical to its exported figure hashes.
This post-processing changes documentation only, never data, figures or runtime.
"""
from pathlib import Path
import runpy
RUN=Path(__file__).resolve().parent
def finalize_readme():
    path=RUN/'README.md';text=path.read_text(encoding='utf8')
    text=text.replace('根地址显示的是目录列表。','当前根地址会跳转到v19页面；为避免打开旧入口，建议使用上述完整地址。')
    text=text.replace("'reproduction/improvement_v19_20261019_01/build_report.py'", "'reproduction/improvement_v19_20261019_01/build_delivery.py'")
    marker='## 只读核验'
    if marker not in text:
        text+='''
## 只读核验

最终交付封存后，从项目根目录执行；不会重跑实验：

```powershell
& '.\\.venv\\Scripts\\python.exe' -B -X utf8 'reproduction/improvement_v19_20261019_01/verify_integrity.py'
```

检查旧文件保留、九份入口备份、当前交付文件及实验源码与结果哈希。
'''
    path.write_text(text,encoding='utf8')
if __name__=='__main__':
    runpy.run_path(str(RUN/'build_report.py'),run_name='__main__')
    finalize_readme()

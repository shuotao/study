#!/usr/bin/env python3
"""N 專案續跑 lint:讀 runs/<run>/STATE.json,重跑各 phase 的 gate,告訴下一個 session 從哪裡接。

用法: n_lint.py <run_dir>
STATE.json 格式: {"phases": {"<name>": {"status": "todo|running|pass|fail|circuit", "round": n,
                  "artifacts": [...], "gates": ["<shell cmd>", ...], "note": "..."}}, "next": "..."}
gates 內的指令在 N 根目錄執行;回傳碼 0 = 綠。
"""
import sys, json, subprocess
from pathlib import Path

N = Path(__file__).resolve().parent.parent


def main():
    run = Path(sys.argv[1]).resolve()
    st = json.loads((run / "STATE.json").read_text(encoding="utf-8"))
    bad = 0
    for name, ph in st["phases"].items():
        missing = [a for a in ph.get("artifacts", []) if not (run / a).exists()]
        gate_rc = []
        if ph.get("status") == "pass":
            for g in ph.get("gates", []):
                rc = subprocess.run(g, shell=True, cwd=N, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL).returncode
                gate_rc.append(rc)
        drift = ph.get("status") == "pass" and (missing or any(gate_rc))
        bad += bool(drift)
        flag = "DRIFT" if drift else ph.get("status", "?").upper()
        print(f"[{flag:7}] {name:22} round={ph.get('round', 0)} "
              f"missing={missing or '-'} gates={gate_rc or '-'} {ph.get('note', '')}")
    print("next:", st.get("next", "?"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

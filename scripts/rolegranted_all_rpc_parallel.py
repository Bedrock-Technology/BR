import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

RPC = os.getenv("BSC_RPC_URL", "").strip()
CONTRACT = "0xff7d6a96ae471bbcd7713af9cb1feeb16cf56b41"
TOPIC_ROLE_GRANTED = "0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d"
START_BLOCK = 47388486  # contract creation block
STEP = 10_000  # provider limit
WORKERS = 6
OUT = "roleGranted_events.csv"


def rpc(method, params, timeout=30):
    s = requests.Session()
    s.trust_env = False
    r = s.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        raise RuntimeError(j["error"])
    return j["result"]


def topic_addr(topic_hex: str) -> str:
    return "0x" + topic_hex[-40:]


def fetch_chunk(start: int, end: int):
    params = [{
        "fromBlock": hex(start),
        "toBlock": hex(end),
        "address": CONTRACT,
        "topics": [TOPIC_ROLE_GRANTED],
    }]

    err = None
    for i in range(6):
        try:
            logs = rpc("eth_getLogs", params, timeout=45)
            rows = []
            for lg in logs:
                topics = lg.get("topics", [])
                rows.append({
                    "blockNumber": int(lg["blockNumber"], 16),
                    "txHash": lg["transactionHash"],
                    "logIndex": int(lg["logIndex"], 16),
                    "role": topics[1] if len(topics) > 1 else "",
                    "account": topic_addr(topics[2]) if len(topics) > 2 else "",
                    "sender": topic_addr(topics[3]) if len(topics) > 3 else "",
                })
            return start, end, rows
        except Exception as e:
            err = e
            time.sleep(min(0.5 + i * 0.8, 4))
    raise RuntimeError(f"chunk {start}-{end} failed: {err}")


def main():
    if not RPC:
        raise RuntimeError("Missing env var: BSC_RPC_URL")

    latest = int(rpc("eth_blockNumber", []), 16)
    print(f"rpc: {RPC}")
    print(f"scan blocks: {START_BLOCK} -> {latest}")

    chunks = []
    cur = START_BLOCK
    while cur <= latest:
        end = min(cur + STEP - 1, latest)
        chunks.append((cur, end))
        cur = end + 1

    all_rows = []
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        future_map = {ex.submit(fetch_chunk, s, e): (s, e) for s, e in chunks}
        for fut in as_completed(future_map):
            s, e = future_map[fut]
            done += 1
            rows = fut.result()
            all_rows.extend(rows[2])
            if done % 100 == 0 or rows[2]:
                print(f"done {done}/{len(chunks)} | chunk {s}-{e} | logs={len(rows[2])} | total={len(all_rows)}", flush=True)

    all_rows.sort(key=lambda x: (x["blockNumber"], x["logIndex"]))

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["blockNumber", "txHash", "logIndex", "role", "account", "sender"])
        w.writeheader()
        w.writerows(all_rows)

    print(f"\nRoleGranted events: {len(all_rows)}")
    print(f"Saved: {OUT}")
    if all_rows:
        print("First:", all_rows[0]["txHash"])
        print("Last:", all_rows[-1]["txHash"])


if __name__ == "__main__":
    main()

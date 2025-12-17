import pandas as pd
from config import ADZUNA_FILTERED_CSV, MERGED_CSV

def main():
    dfs = []

    try:
        df1 = pd.read_csv(ADZUNA_FILTERED_CSV)
        dfs.append(df1)
        print(f"[MERGE] Adzuna: {len(df1)} rows")
    except:
        print("[MERGE] No Adzuna file.")

    try:
        df2 = pd.read_csv("data/jooble_jobs_filtered.csv")
        dfs.append(df2)
        print(f"[MERGE] Jooble: {len(df2)} rows")
    except:
        print("[MERGE] No Jooble file.")

    if not dfs:
        print("[MERGE] No files to merge.")
        return

    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=["url"])
    df.to_csv(MERGED_CSV, index=False)
    print(f"[MERGE] Final saved: {len(df)}")

if __name__ == "__main__":
    main()

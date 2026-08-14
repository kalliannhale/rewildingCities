"""
field-guide/ade_labelmap_to_json.py
Convert ADE20K's objectInfo150.txt (ships inside ADEChallengeData2016) into the
{index: name} JSON that train_segmenter_head's corpus_label_map expects.

objectInfo150.txt is tab-separated with a header row:
    Idx  Ratio  Train  Val  Name
Name is the last column and may itself contain commas (synonym lists), which is
fine, the synonym-aware remap in train_segmenter_head handles them.

Usage:
    python ade_labelmap_to_json.py \
        ADEChallengeData2016/objectInfo150.txt \
        ADEChallengeData2016/ade_index_to_name.json
"""
import csv
import json
import sys


def main():
    src, dst = sys.argv[1], sys.argv[2]
    out = {}
    with open(src, newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row:
                continue
            idx = row[0].strip()
            if not idx.isdigit():        # skips the header row
                continue
            out[int(idx)] = row[-1].strip()
    with open(dst, "w") as f:
        json.dump(out, f, indent=0, ensure_ascii=False)
    print(f"wrote {len(out)} classes -> {dst}")
    # spot-check a few that matter for the crosswalk
    for i in (5, 7, 10, 14, 18, 22):
        if i in out:
            print(f"  {i}: {out[i]}")


if __name__ == "__main__":
    main()

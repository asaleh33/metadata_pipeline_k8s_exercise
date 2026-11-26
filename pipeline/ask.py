"""
Ask the database for any metadata value, for every processed image.

    python ask.py AP_MAG AP_WD          the values of these keys, one line per image
    python ask.py --keys MAG            the key names that contain "MAG" (and how many images have them)
    python ask.py --keys                all the key names in the database
    (--key and -k work as well as --keys)

Every image's whole metadata is in the database (column images.metadata),
so any key can be asked for, not only the ones in variables.json.
"""
import sys

import db


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    unknown = [a for a in args[1:] if a.startswith("-")] + ([args[0]] if args[0].startswith("-") and args[0] not in ("--keys", "--key", "-k") else [])
    if unknown:
        raise SystemExit(f"unknown option {unknown[0]}\n" + __doc__)
    conn = db.connect(wait_s=10)      # a quick question: don't wait long if the database is not there

    if args[0] in ("--keys", "--key", "-k"):
        part = args[1] if len(args) > 1 else ""
        rows = db.find_keys(conn, part)
        print(f"{'KEY':<34} IMAGES")
        for key, n in rows:
            print(f"{key:<34} {n}")
        print(f"\n{len(rows)} keys" + (f" containing '{part}'" if part else ""))
        return

    rows = db.ask(conn, args)
    widths = [max([len(k)] + [len(str(r[k] or "-")) for r in rows]) for k in args]
    print(f"{'IMAGE':<24} {'CATEGORY':<22} " + "  ".join(f"{k:<{w}}" for k, w in zip(args, widths)))
    for r in rows:
        print(f"{r['image'][:23]:<24} {(r['category'] or '-')[:21]:<22} "
              + "  ".join(f"{str(r[k] or '-'):<{w}}" for k, w in zip(args, widths)))


if __name__ == "__main__":
    main()

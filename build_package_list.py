from glob import glob
import json

REPO_TAG = "github:sandal-tan/breadboard/"


def main():
    source_files = glob("breadboard/**.py")
    if source_files:
        with open("./package.json", "r+") as fp:
            obj = json.load(fp)
            obj["urls"] = [[f, REPO_TAG + f] for f in source_files]
            fp.seek(0)
            json.dump(obj, fp, indent=4)
    else:
        ...


if __name__ == "__main__":
    main()

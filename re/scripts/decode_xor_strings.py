#!/usr/bin/env python3
"""BackupToolkit v1.1.1 —— 字符串去混淆脚本（分析用，非产品代码）。

样本 p004class.Cwhile 的反射字符串由 p005const.Cthrow.m914true(char...) 解密：
    key = ((1047 ^ 1113) ^ len(packageName)) + 13      # 1047/1113 = 该构建的 versionCode 片段
    for i in range(len(arr) - 1): arr[i] ^= key        # 最后一个字符不参与异或
本脚本按源码中的字符数组还原出全部明文，用于核对「签名自校验」逻辑。

用法:  python decode_xor_strings.py
"""
KEY = ((1047 ^ 1113) ^ len("r2ixzp.toolkit")) + 13  # == 77 == 'M'

# 直接抄自 re/jadx/sources/p004class/Cwhile.java 的 m914true(...) 实参
ARRAYS = {
    "pm_getter":       [42, 40, 57, 29, 44, 46, 38, 44, 42, 40, 0, 44, 35, 44, 42, 40, 114],
    "getPackageInfo":  [42, 40, 57, 29, 44, 46, 38, 44, 42, 40, 4, 35, 43, 111],
    "signatures":      [62, 36, 42, 35, 44, 57, 56, 63, 40, 115],
    "toByteArray":     [57, 34, 15, 52, 57, 40, 12, 63, 63, 44, 121],
    "MessageDigest":   [39, 44, 59, 44, 99, 62, 40, 46, 56, 63, 36, 57, 52, 99, 0, 40, 62, 62, 44, 42, 40, 9, 36, 42, 40, 62, 116],
    "getInstance":     [42, 40, 57, 4, 35, 62, 57, 44, 35, 46, 101],
    "SHA256":          [30, 5, 12, 96, 127, 120, 54],
    "update":          [56, 61, 41, 44, 57, 101],
    "expected_b64":    [126, 30, 20, 7, 11, 43, 37, 37, 33, 0, 120, 125, 37, 4, 43, 21, 5, 40, 40, 3, 29, 116, 61, 117, 5, 39, 57, 117, 33, 3, 9, 43, 12, 120, 42, 62, 15, 21, 15, 126, 14, 10, 62, 61],
    "Base64":          [44, 35, 41, 63, 34, 36, 41, 99, 56, 57, 36, 33, 99, 15, 44, 62, 40, 123, 52],
    "encodeToString":  [40, 35, 46, 34, 41, 40, 25, 34, 30, 57, 63, 36, 35, 103],
    "digest":          [41, 36, 42, 40, 62, 116],
}


def decrypt(arr):
    out = []
    for i, c in enumerate(arr):
        out.append(chr(c ^ KEY) if i < len(arr) - 1 else chr(c))
    return "".join(out)


if __name__ == "__main__":
    print(f"key = {KEY} ('{chr(KEY)}')")
    for name, arr in ARRAYS.items():
        print(f"{name:16s} -> {decrypt(arr)}")

#!/usr/bin/env python3
"""Build and verify a storage-blind static AArch64 PID 1."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import tempfile
import time


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_ROOT = (ROOT / "out").resolve()
ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
PROGRAM_HEADER = struct.Struct("<IIQQQQQQ")
ELFCLASS64 = 2
ELFDATA2LSB = 1
ET_EXEC = 2
EM_AARCH64 = 183
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_GNU_STACK = 0x6474E551
PF_X = 1
PF_W = 2
SVC_ZERO = 0xD4000001
SVC_OPCODE_MASK = 0xFFE0001F
MOV_X8_WRITE = 0xD2800808
MOV_X8_NANOSLEEP = 0xD2800CA8
MARKER = b"STREMIO_VERO_SAFE_PROBE: kernel, DTB and initramfs reached; storage untouched.\n"
FORBIDDEN_PAYLOADS = (
    b"/dev/",
    b"busybox",
    b"/bin/",
    b"/sbin/",
    b"mount",
    b"fsck",
    b"flash",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_output(path: pathlib.Path) -> pathlib.Path:
    resolved_parent = path.parent.resolve()
    if OUT_ROOT != resolved_parent and OUT_ROOT not in resolved_parent.parents:
        raise ValueError("output must be inside the repository out directory")
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise ValueError("existing output is not a regular file")
    return path


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise ValueError(f"required pinned-runner tool is missing: {name}")
    return path


def tool_version(path: str) -> str:
    result = subprocess.run(
        [path, "--version"], check=False, capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError(f"could not identify tool version: {pathlib.Path(path).name}")
    return result.stdout.splitlines()[0]


def run(command: list[str]) -> None:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"tool failed ({pathlib.Path(command[0]).name}): {detail}")


def program_headers(blob: bytes) -> tuple[int, list[dict[str, int]]]:
    if len(blob) < ELF_HEADER.size:
        raise ValueError("probe init is not a complete ELF64 file")
    values = ELF_HEADER.unpack_from(blob)
    ident = values[0]
    if ident[:4] != b"\x7fELF" or ident[4] != ELFCLASS64 or ident[5] != ELFDATA2LSB:
        raise ValueError("probe init must be little-endian ELF64")
    elf_type, machine, version = values[1:4]
    entry, program_offset = values[4], values[5]
    header_size, program_entry_size, program_count = values[8:11]
    if elf_type != ET_EXEC or machine != EM_AARCH64 or version != 1:
        raise ValueError("probe init must be an AArch64 ET_EXEC file")
    if header_size != ELF_HEADER.size or program_entry_size != PROGRAM_HEADER.size:
        raise ValueError("probe init has unexpected ELF header sizes")
    if not 1 <= program_count <= 16:
        raise ValueError("probe init has an unexpected program-header count")

    headers: list[dict[str, int]] = []
    for index in range(program_count):
        offset = program_offset + index * program_entry_size
        if offset + PROGRAM_HEADER.size > len(blob):
            raise ValueError("probe init has a truncated program header")
        fields = PROGRAM_HEADER.unpack_from(blob, offset)
        header = {
            "type": fields[0],
            "flags": fields[1],
            "offset": fields[2],
            "vaddr": fields[3],
            "filesz": fields[5],
            "memsz": fields[6],
        }
        if header["filesz"] > header["memsz"]:
            raise ValueError("probe init segment file size exceeds memory size")
        if header["offset"] + header["filesz"] > len(blob):
            raise ValueError("probe init segment exceeds the ELF file")
        headers.append(header)
    return entry, headers


def verify_probe_elf(blob: bytes) -> dict[str, object]:
    entry, headers = program_headers(blob)
    if any(header["type"] in {PT_DYNAMIC, PT_INTERP} for header in headers):
        raise ValueError("probe init must not have a dynamic loader or interpreter")
    load_headers = [header for header in headers if header["type"] == PT_LOAD]
    if not load_headers:
        raise ValueError("probe init has no loadable segment")
    if any(header["flags"] & PF_W and header["flags"] & PF_X for header in load_headers):
        raise ValueError("probe init has a writable and executable segment")
    stack_headers = [header for header in headers if header["type"] == PT_GNU_STACK]
    if len(stack_headers) != 1 or stack_headers[0]["flags"] & PF_X:
        raise ValueError("probe init must declare one non-executable stack")
    executable = [header for header in load_headers if header["flags"] & PF_X]
    if not any(header["vaddr"] <= entry < header["vaddr"] + header["memsz"] for header in executable):
        raise ValueError("probe init entry point is not in an executable segment")

    syscall_instructions: list[int] = []
    for header in executable:
        segment = blob[header["offset"] : header["offset"] + header["filesz"]]
        for offset in range(0, len(segment) - 3, 4):
            instruction = struct.unpack_from("<I", segment, offset)[0]
            if instruction & SVC_OPCODE_MASK == SVC_ZERO:
                if instruction != SVC_ZERO:
                    raise ValueError("probe init contains an SVC with a nonzero immediate")
                if offset < 4:
                    raise ValueError("probe init syscall has no immediate setup")
                syscall_instructions.append(struct.unpack_from("<I", segment, offset - 4)[0])
    if syscall_instructions != [MOV_X8_WRITE, MOV_X8_NANOSLEEP]:
        raise ValueError("probe init must contain exactly write and nanosleep syscall sites")
    if blob.count(MARKER) != 1:
        raise ValueError("probe init does not contain exactly one safety marker")
    if any(payload in blob for payload in FORBIDDEN_PAYLOADS):
        raise ValueError("probe init contains a forbidden filesystem or maintenance payload")
    return {
        "format": "static-elf64-aarch64",
        "entry": f"0x{entry:x}",
        "syscalls": ["write", "nanosleep"],
        "marker": MARKER.decode("ascii").rstrip(),
        "sha256": sha256_bytes(blob),
    }


def build_once(source: pathlib.Path, directory: pathlib.Path, tools: dict[str, str]) -> bytes:
    obj = directory / "init.o"
    binary = directory / "init"
    run([tools["as"], "--fatal-warnings", "-o", str(obj), str(source)])
    run(
        [
            tools["ld"],
            "-nostdlib",
            "-static",
            "--build-id=none",
            "-z",
            "noexecstack",
            "-e",
            "_start",
            "-Ttext=0x400000",
            "-o",
            str(binary),
            str(obj),
        ]
    )
    run([tools["strip"], "--strip-all", str(binary)])
    return binary.read_bytes()


def verify_with_qemu(qemu: str, binary: pathlib.Path) -> None:
    process = subprocess.Popen(
        [qemu, "-strace", str(binary)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(0.5)
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        raise ValueError(
            "probe init exited instead of remaining PID 1: "
            + (stderr or stdout).decode("utf-8", errors="replace").strip()
        )
    process.terminate()
    try:
        stdout, stderr = process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=2)
    if stdout != MARKER:
        raise ValueError("QEMU probe did not emit the exact safety marker")
    trace = stderr.decode("utf-8", errors="replace")
    syscall_lines = [line for line in trace.splitlines() if "(" in line and ")" in line]
    if not any(" write(" in line for line in syscall_lines):
        raise ValueError("QEMU trace did not observe write")
    if not any(" nanosleep(" in line for line in syscall_lines):
        raise ValueError("QEMU trace did not observe nanosleep")
    allowed = (" write(", " nanosleep(")
    unexpected = [line for line in syscall_lines if not any(name in line for name in allowed)]
    if unexpected:
        raise ValueError(f"QEMU trace observed unexpected syscalls: {unexpected}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--qemu", default=None)
    args = parser.parse_args()
    source = (ROOT / args.source).resolve() if not args.source.is_absolute() else args.source.resolve()
    if ROOT != source.parent and ROOT not in source.parents:
        raise ValueError("probe init source must be inside the repository")
    output = safe_output(
        (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output
    )
    tools = {
        "as": require_tool("aarch64-linux-gnu-as"),
        "ld": require_tool("aarch64-linux-gnu-ld"),
        "strip": require_tool("aarch64-linux-gnu-strip"),
    }
    tool_versions = {name: tool_version(path) for name, path in tools.items()}
    with tempfile.TemporaryDirectory(prefix="stremio-vero-init-a-") as first_dir, tempfile.TemporaryDirectory(
        prefix="stremio-vero-init-b-"
    ) as second_dir:
        first = build_once(source, pathlib.Path(first_dir), tools)
        second = build_once(source, pathlib.Path(second_dir), tools)
    if first != second:
        raise ValueError("probe init is not reproducible across two clean builds")
    details = verify_probe_elf(first)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(first)
    output.chmod(0o755)
    if args.qemu:
        verify_with_qemu(require_tool(args.qemu), output)
        details["qemu_runtime_check"] = "passed"
    else:
        details["qemu_runtime_check"] = "not-run"
    details.update(
        {
            "schema": 1,
            "artifact": output.name,
            "source_sha256": sha256_bytes(source.read_bytes()),
            "same_toolchain_double_build_identical": True,
            "tool_versions": tool_versions,
            "physical_boot_tested": False,
        }
    )
    output.with_suffix(output.suffix + ".manifest.json").write_text(
        json.dumps(details, indent=2) + "\n", encoding="utf-8"
    )
    print(f"storage-blind AArch64 init: PASS ({details['sha256']})")
    print("allowed syscalls: write, nanosleep")
    for name, version in tool_versions.items():
        print(f"{name} tool: {version}")
    print("physical boot status: NOT TESTED")


if __name__ == "__main__":
    main()

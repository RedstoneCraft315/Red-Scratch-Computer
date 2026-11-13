"""Assembler core for the standalone Compiler 2 application."""

from dataclasses import dataclass
import os
import re


MNEMONICS = (
    "NOP", "LDA", "LDB", "LDC", "RTA", "RTB", "RTC", "ATR", "BTR",
    "CTR", "ADD", "JMP", "BEQ", "RTD", "PRV", "MLT", "SUB", "DIV",
    "KTR", "CLD", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "SRL",
    "SRR", "MOD",
)
OPCODES = {
    "NOP": 0x00, "LDA": 0xA0, "LDB": 0xB0, "LDC": 0xC0,
    "RTA": 0xA1, "RTB": 0xB1, "RTC": 0xC1, "ATR": 0xA2,
    "BTR": 0xB2, "CTR": 0xC2, "ADD": 0x40, "JMP": 0x10,
    "BEQ": 0x11, "RTD": 0xD0, "PRV": 0x00, "MLT": 0x41,
    "SUB": 0x42, "DIV": 0x43, "KTR": 0xD1, "CLD": 0xD2,
    "AND": 0x60, "OR": 0x61, "XOR": 0x62, "NOT": 0x63,
    "SHL": 0x64, "SHR": 0x65, "SRL": 0x66, "SRR": 0x67,
    "MOD": 0x44,
}
OPERAND_COUNTS = {
    "NOP": 0, "LDA": 1, "LDB": 1, "LDC": 1, "RTA": 1, "RTB": 1,
    "RTC": 1, "ATR": 1, "BTR": 1, "CTR": 1, "ADD": 0, "JMP": 1,
    "BEQ": 1, "RTD": 3, "PRV": 0, "MLT": 0, "SUB": 0, "DIV": 0,
    "KTR": 0, "CLD": 0, "AND": 0, "OR": 0, "XOR": 0, "NOT": 0,
    "SHL": 0, "SHR": 0, "SRL": 0, "SRR": 0, "MOD": 0,
}
LABEL_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass(frozen=True)
class Diagnostic:
    line: int
    message: str


@dataclass
class AssemblyResult:
    output: str
    words: list
    diagnostics: list

    @property
    def succeeded(self):
        return not self.diagnostics


def tokenize_line(line):
    """Split assembly code into tokens, ignoring a semicolon comment."""
    code = line.split(";", 1)[0]
    return code.replace(",", " ").split()


def parse_number(token):
    """Read the compiler's established hexadecimal operand notation."""
    value = token.strip()
    if not value:
        return None
    if value.lower().startswith("0x"):
        try:
            return int(value, 16)
        except ValueError:
            return None
    if value.endswith(("h", "H")):
        try:
            return int(value[:-1], 16)
        except ValueError:
            return None
    if len(value) > 1 and value.startswith("0") and all(
        char in "0123456789abcdefABCDEF" for char in value
    ):
        try:
            return int(value, 16)
        except ValueError:
            return None
    try:
        return int(value, 16)
    except ValueError:
        try:
            return int(value, 10)
        except ValueError:
            return None


def format_logisim(words):
    """Format words using Logisim's addressed hexadecimal memory format."""
    padded = list(words)
    padded.extend([0] * max(0, 16 - len(padded)))
    if len(padded) % 8:
        padded.extend([0] * (8 - len(padded) % 8))

    lines = ["v3.0 hex words addressed"]
    for address in range(0, len(padded), 8):
        chunk = " ".join(f"{word:04X}" for word in padded[address:address + 8])
        lines.append(f"{address:04X}: {chunk}")
    return "\n".join(lines) + "\n"


def disassemble_words(words):
    reverse_opcodes = {}
    for mnemonic, opcode in OPCODES.items():
        if opcode not in reverse_opcodes or mnemonic == "NOP":
            reverse_opcodes[opcode] = mnemonic

    instructions = []
    word_index = 0
    while word_index < len(words):
        opcode = words[word_index]
        if opcode > 0xFF or opcode not in reverse_opcodes:
            return None
        mnemonic = reverse_opcodes[opcode]
        operand_count = OPERAND_COUNTS[mnemonic]
        end = word_index + 1 + operand_count
        if end > len(words):
            return None
        instructions.append((word_index, mnemonic, words[word_index + 1:end]))
        word_index = end

    instruction_addresses = {address for address, _, _ in instructions}
    jump_targets = {
        operands[0]
        for _, mnemonic, operands in instructions
        if mnemonic in ("JMP", "BEQ")
        and operands
        and operands[0] in instruction_addresses | {len(words)}
    }

    lines = []
    for address, mnemonic, operands in instructions:
        if address in jump_targets:
            lines.append(f"RAW_{address:04X}:")
        if mnemonic in ("JMP", "BEQ") and operands and operands[0] in jump_targets:
            rendered_operands = [f"RAW_{operands[0]:04X}"]
        else:
            rendered_operands = [f"0x{value:04X}" for value in operands]
        lines.append(" ".join([mnemonic] + rendered_operands))
    if len(words) in jump_targets:
        lines.append(f"RAW_{len(words):04X}:")
    return "\n".join(lines)


def disassemble_raw_bytes(data):
    if len(data) % 2:
        return None

    candidates = []
    for byteorder in ("big", "little"):
        words = [
            int.from_bytes(data[index:index + 2], byteorder)
            for index in range(0, len(data), 2)
        ]
        assembly = disassemble_words(words)
        if assembly is not None:
            candidates.append(assembly)
    if candidates and all(candidate == candidates[0] for candidate in candidates):
        return candidates[0]
    return None


def hex_words_from_text(text):
    words = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("v"):
            continue
        if ":" in line:
            _, line = line.split(":", 1)
        tokens = line.split()
        if not tokens or any(not re.fullmatch(r"[0-9a-fA-F]{1,4}", token) for token in tokens):
            return None
        words.extend(int(token, 16) for token in tokens)
    return words if words else None


def format_hex_words(words):
    lines = ["; Raw hex data (words):"]
    lines.extend(
        "; " + " ".join(f"{word:04X}" for word in words[index:index + 16])
        for index in range(0, len(words), 16)
    )
    return "\n".join(lines)


def source_from_inserted_file(path):
    with open(path, "rb") as source_file:
        data = source_file.read()

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None

    if text is not None and "\x00" not in text and all(
        char in "\t\r\n" or ord(char) >= 32 for char in text
    ):
        if os.path.splitext(path)[1].lower() == ".hex":
            words = hex_words_from_text(text)
            if words is not None:
                assembly = disassemble_words(words)
                if assembly is not None:
                    return assembly
                return format_hex_words(words)
        return text

    assembly = disassemble_raw_bytes(data)
    if assembly is not None:
        return assembly

    hex_bytes = " ".join(f"{value:02X}" for value in data)
    return "\n".join(
        ["; Raw file data (hex):"]
        + [f"; {hex_bytes[index:index + 96]}" for index in range(0, len(hex_bytes), 96)]
    )


def assemble(source):
    """Assemble source text, resolving labels and numeric jump line targets."""
    lines = source.splitlines()
    if not lines:
        return AssemblyResult("", [], [Diagnostic(1, "Source is empty.")])

    token_lines = [tokenize_line(line) for line in lines]
    line_addresses = []
    labels = {}
    diagnostics = []
    address = 0

    for line_number, tokens in enumerate(token_lines, start=1):
        line_addresses.append(address)
        token_index = 0
        if tokens and tokens[0].endswith(":"):
            label = tokens[0][:-1]
            if not LABEL_PATTERN.fullmatch(label):
                diagnostics.append(Diagnostic(line_number, f"Invalid label name: {label!r}."))
            elif label.upper() in labels:
                diagnostics.append(Diagnostic(line_number, f"Duplicate label: {label}."))
            else:
                labels[label.upper()] = address
            token_index = 1

        if token_index >= len(tokens):
            continue

        mnemonic = tokens[token_index].upper()
        if mnemonic not in OPCODES:
            diagnostics.append(Diagnostic(line_number, f"Unknown instruction: {tokens[token_index]}."))
            address += 1
            continue

        operand_count = len(tokens) - token_index - 1
        expected_count = OPERAND_COUNTS[mnemonic]
        if operand_count != expected_count:
            diagnostics.append(Diagnostic(
                line_number,
                f"{mnemonic} expects {expected_count} operand(s), got {operand_count}.",
            ))
        address += 1 + expected_count
        if address > 0x10000:
            diagnostics.append(Diagnostic(line_number, "Program exceeds the 65,536-word address space."))
            break

    if address > 0x10000:
        return AssemblyResult("", [], diagnostics)

    words = []
    for line_number, tokens in enumerate(token_lines, start=1):
        token_index = 1 if tokens and tokens[0].endswith(":") else 0
        if token_index >= len(tokens):
            continue

        mnemonic = tokens[token_index].upper()
        if mnemonic not in OPCODES:
            continue
        operands = tokens[token_index + 1:]
        if len(operands) != OPERAND_COUNTS[mnemonic]:
            continue

        resolved = []
        line_has_error = False
        for operand in operands:
            label_address = labels.get(operand.upper())
            if label_address is not None:
                value = label_address
            else:
                value = parse_number(operand)
                if value is None:
                    diagnostics.append(Diagnostic(line_number, f"Unknown label or number: {operand}."))
                    line_has_error = True
                    continue
                if mnemonic in ("JMP", "BEQ") and 0 <= value < len(lines):
                    value = line_addresses[value]
            if not 0 <= value <= 0xFFFF:
                diagnostics.append(Diagnostic(
                    line_number,
                    f"Operand {operand!r} is outside the 16-bit range (0x0000-0xFFFF).",
                ))
                line_has_error = True
                continue
            resolved.append(value)

        if not line_has_error and len(resolved) == len(operands):
            words.append(OPCODES[mnemonic])
            words.extend(resolved)

    if diagnostics:
        return AssemblyResult("", [], diagnostics)
    return AssemblyResult(format_logisim(words), words, [])

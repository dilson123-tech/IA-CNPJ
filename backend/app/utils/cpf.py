import re


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def mask_cpf(cpf: str) -> str:
    digits = only_digits(cpf)

    if len(digits) != 11:
        return cpf

    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def is_valid_cpf(cpf: str) -> bool:
    digits = only_digits(cpf)

    if len(digits) != 11:
        return False

    if digits == digits[0] * 11:
        return False

    def calculate_digit(base: str) -> str:
        weight = len(base) + 1
        total = sum(int(num) * (weight - idx) for idx, num in enumerate(base))
        remainder = total % 11
        digit = 0 if remainder < 2 else 11 - remainder
        return str(digit)

    first_digit = calculate_digit(digits[:9])
    second_digit = calculate_digit(digits[:9] + first_digit)

    return digits[-2:] == first_digit + second_digit

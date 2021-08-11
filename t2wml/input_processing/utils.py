from string import punctuation

def check_special_characters(text: str) -> bool:
    return all(char in punctuation for char in str(text))

def string_is_valid(text: str) -> bool:
    text=str(text)
    if not text:
        return False
    text = text.strip().lower()
    if check_special_characters(text):
        return False
    if text in ["", "#na", "nan"]:
        return False
    return True

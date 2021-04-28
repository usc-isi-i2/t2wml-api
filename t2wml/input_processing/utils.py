from string import punctuation
def string_is_valid(text: str) -> bool:
    def check_special_characters(text: str) -> bool:
        return all(char in punctuation for char in str(text))
    if text is None or check_special_characters(text):
        return False
    text = text.strip().lower()
    if text in ["", "#na", "nan"]:
        return False
    return True

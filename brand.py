class Brand:
    """A beauty brand, e.g. Fenty Beauty or Dior.

    Association with Product: a product refers to its Brand, but neither owns the
    other. Products of the same brand share one Brand object.
    """

    def __init__(self, name: str, country: str = ""):
        name = str(name).strip()
        if not name:
            raise ValueError("Brand name cannot be empty.")
        self.__name: str = name
        self.__country: str = str(country).strip()

    def get_name(self) -> str:
        return self.__name

    def get_country(self) -> str:
        return self.__country

    def display_information(self) -> None:
        country = f" ({self.__country})" if self.__country else ""
        print(f"Brand: {self.__name}{country}")

    def to_dict(self) -> dict:
        """Return the brand's data as a dictionary (used when saving)."""
        return {"name": self.__name, "country": self.__country}

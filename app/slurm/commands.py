from dataclasses import dataclass


@dataclass(frozen=True)
class SlurmCommand:
    executable: str
    arguments: tuple[str, ...] = ()

    def as_list(self) -> list[str]:
        return [self.executable, *self.arguments]


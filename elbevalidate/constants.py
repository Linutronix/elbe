import enum


class PartitionLabel(enum.StrEnum):
    DOS = 'msdos'
    GPT = 'gpt'


class GPTPartitionType(str):
    EFI_SYSTEM_PARTITION = 'C12A7328-F81F-11D2-BA4B-00A0C93EC93B'
    LINUX_FILESYSTEM = '0FC63DAF-8483-4772-8E79-3D69D8477DE4'

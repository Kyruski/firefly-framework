from __future__ import annotations


class RepositoryError(Exception):
    pass


class NoResultFound(RepositoryError):
    pass


class MultipleResultsFound(RepositoryError):
    pass


class FrameworkError(Exception):
    pass


class ProjectConfigNotFound(FrameworkError):
    pass


class ProviderNotFound(FrameworkError):
    pass


class InvalidArgument(FrameworkError):
    pass


class MissingRouter(FrameworkError):
    pass


class MessageBusError(FrameworkError):
    pass

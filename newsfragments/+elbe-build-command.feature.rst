Add a new ``elbe build`` command as a VM-free alternative to ``elbe initvm submit``.
It drives the project manager directly in-process, without any daemon or SOAP
communication, and is meant to be used inside a container (or any other environment)
that already provides the isolation an initvm would otherwise provide.

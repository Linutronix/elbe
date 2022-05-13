Use ELBE with Jenkins on a k8s cluster
======================================

ELBE can also be used on a Jenkins/k8s based CI.

For setting up the infrastructure, see e.g.
https://jenkinsci.github.io/kubernetes-operator/

Additionaly these resources are needed on the cluster if
the binfmt_misc kernel module is not loaded by default in
the cluster nodes:

vm-modules-pvc.yaml
vm-modules-pv.yaml

A global shared library named 'elbe' needs to be configured.
It shall point to the elbe git repo and use the subpath
'contrib/k8s/jenkins-shared-lib'.

https://www.jenkins.io/doc/book/pipeline/shared-libraries/

Dockerfile
----------
Image that includes the needed parts of elbe.
It shall be built and put to the the container registry of the cluster.

jenkins-shared-lib
------------------
The shared lib expects, that the Jenkins environment includes
a variable 'DOCKER_REGISTRY' that points to the base url of the
used container registry.



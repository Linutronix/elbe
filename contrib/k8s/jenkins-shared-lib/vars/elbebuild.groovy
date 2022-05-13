def call(String elbexml, Boolean buildsdk)
{
  def podlabel = "elbe-${elbexml}-${UUID.randomUUID().toString()}"

  properties([disableResume()])

  podTemplate(label       : "${podlabel}",
              podRetention: onFailure(),
              containers  : [containerTemplate(name                 : 'elbe',
                                               image                : "${env.DOCKER_REGISTRY}/elbeimage:latest",
                                               alwaysPullImage      : true,
                                               resourceRequestCpu   : '2000m',
                                               resourceRequestMemory: '16Gi',
                                               resourceLimitCpu     : '2000m',
                                               resourceLimitMemory  : '16Gi',
                                               ttyEnabled           : true,
                                               privileged           : true,
                                               command              : 'cat'),
                            ],
              envVars     : [containerEnvVar(key  : 'HOME',
                                             value: '/home/jenkins/agent'),
                            ],
              volumes     : [persistentVolumeClaim(claimName        : 'vm-modules-pvc',
                                                   mountPath        : '/lib/modules'),
                            ],
             )
  {
    node ("${podlabel}") {
      stage('checkout') {
        def gitscm = checkout scm
        env.GIT_BRANCH = gitscm.GIT_BRANCH
      }
      container('elbe') {
        stage('load kernel modules') {
          sh "modprobe binfmt_misc"
          sh "update-binfmts --enable qemu-arm"
        }
        stage('elbe image build') {
          sh "test -d archive && elbe chg_archive ${elbexml} archive || /bin/true"
          sh "elbe buildchroot -t image ${elbexml}"
        }
        stage('elbe SDK build') {
          if (buildsdk) {
            sh "elbe buildsdk image"
          }
        }
        stage('store artifacts') {
          sh "rm -rf image/chroot image/target image/repo image/sysroot"
          archiveArtifacts artifacts: "image/*"
        }
      }
    }
  }
}

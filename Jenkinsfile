pipeline {
  agent any
  stages {
    stage('setup') {
      steps {
        echo 'SET VENV'
        echo 'PIP INSTALL'
      }
    }
    stage('stop') {
      steps {
        echo 'STOP APP SERVICE'
      }
    }
    stage('deploy') {
      steps {
        echo 'COPY FILES TO SETUP PATH'
      }
    }
    stage('start') {
      steps {
        echo 'START APP SERVICE'
      }
    }
  }
}
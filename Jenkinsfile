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
        sh 'sudo systemctl stop scholarly-wallet-ws'
      }
    }
    stage('deploy') {
      environment {
        SW_WS_PATH = credentials('sw-ws-path')
      }
      steps {
        sh 'cp -p -r ./* $SW_WS_PATH'
      }
    }
    stage('start') {
      steps {
        echo 'START APP SERVICE'
        sh 'sudo systemctl start scholarly-wallet-ws'
      }
    }
  }
}
#!/bin/env python
import os

#
# Example script to submit TnPTreeProducer to crab
#
submitVersion = "2025-07-05" # add some date here
doL1matching  = False
isAOD = False

defaultArgs = ['doEleID=False','doPhoID=False','doTrigger=True']
AODArgs     = ['isAOD=False','doRECO=False']
mainOutputDir = '/store/user/jmotta/HHbbtautau_Run3/EGM/tnpTuples/%s' % (submitVersion)
mainOutputDir_eospath = '/eos/cms/store/group/phys_higgs/jmotta/HHbbtautau_Run3/EGM/tnpTuples/%s' % (submitVersion)


# Logging the current version of TnpTreeProducer here, such that you can find back what the actual code looked like when you were submitting
os.system('mkdir -p %s' % mainOutputDir_eospath)
os.system('(git log -n 1;git diff) &> %s/git.log' % mainOutputDir_eospath)


#
# Common CRAB settings
#
from CRABClient.UserUtilities import config
config = config()

config.General.requestName             = ''
config.General.transferLogs            = False
config.General.workArea                = '/eos/cms/store/group/phys_higgs/jmotta/HHbbtautau_Run3/EGM/LogFiles/crab_%s' % submitVersion

config.JobType.pluginName              = 'Analysis'
config.JobType.psetName                = '../python/TnPTreeProducer_cfg.py'
config.JobType.sendExternalFolder      = True
config.JobType.allowUndistributedCMSSW = True

config.Data.inputDataset               = ''
config.Data.inputDBS                   = 'global'
config.Data.publication                = False
config.Data.allowNonValidInputDataset  = True
config.Site.storageSite                = 'T3_CH_CERNBOX'


#
# Certified lumis for the different eras
#   (seems the JSON for UL2017 is slightly different from rereco 2017, it's not documented anywhere though)
#
def getLumiMask(era):
  if   era=='2016':   return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions16/13TeV/ReReco/Final/Cert_271036-284044_13TeV_23Sep2016ReReco_Collisions16_JSON.txt'
  elif era=='2017':   return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions17/13TeV/ReReco/Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON_v1.txt'
  elif era=='2018':   return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions18/13TeV/PromptReco/Cert_314472-325175_13TeV_PromptReco_Collisions18_JSON.txt'
  elif era=='UL2016preVFP': return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions16/13TeV/Legacy_2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt'
  elif era=='UL2016postVFP': return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions16/13TeV/Legacy_2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt'
  elif era=='UL2017': return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions17/13TeV/Legacy_2017/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt'
  elif era=='UL2018': return 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions18/13TeV/PromptReco/Cert_314472-325175_13TeV_PromptReco_Collisions18_JSON.txt'
  elif '2022' in era: return 'https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/Cert_Collisions2022_355100_362760_Golden.json'
  elif '2023' in era: return 'https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/Cert_Collisions2023_366442_370790_Golden.json'


#
# Submit command
#
from CRABAPI.RawCommand import crabCommand
from CRABClient.ClientExceptions import ClientException
from http.client import HTTPException

def submit(config, requestName, sample, era, json, extraParam=[]):
  isMC                        = 'SIM' in sample
  config.General.requestName  = '%s_%s' % (era, requestName)
  config.Data.inputDataset    = sample
  config.Data.outLFNDirBase   = '%s/%s/%s/' % (mainOutputDir, era, 'mc' if isMC else 'data')
  config.Data.splitting       = 'FileBased' if isMC else 'LumiBased'
  config.Data.lumiMask        = None if isMC else json
  config.Data.unitsPerJob     = 5 if isMC else 25
  config.JobType.pyCfgParams  = (defaultArgs if not isAOD else AODArgs) + ['isMC=True' if isMC else 'isMC=False', 'era=%s' % era] + extraParam

  print( config )
  try:                           crabCommand('submit', config = config)
  except HTTPException as hte:   print( "Failed submitting task: %s" % (hte.headers))
  except ClientException as cle: print( "Failed submitting task: %s" % (cle))
  print()
  print()

#
# Wrapping the submit command
# In case of doL1matching=True, vary the L1Threshold and use sub-json
#
from multiprocessing import Process
def submitWrapper(requestName, sample, era, extraParam=[]):
  if doL1matching:
    from getLeg1ThresholdForDoubleEle import getLeg1ThresholdForDoubleEle
    for leg1Threshold, json in getLeg1ThresholdForDoubleEle(era.replace("UL","").replace("preVFP","").replace("postVFP","")):
      print( 'Submitting for leg 1 threshold %s' % (leg1Threshold))
      p = Process(target=submit, args=(config, '%s_leg1Threshold%s' % (requestName, leg1Threshold), sample, era, json, extraParam + ['L1Threshold=%s' % leg1Threshold]))
      p.start()
      p.join()
  else:
    p = Process(target=submit, args=(config, requestName, sample, era, getLumiMask(era), extraParam))
    p.start()
    p.join()
    #submit(config, requestName, sample, era, getLumiMask(era), extraParam) # print the config files


#
# List of samples to submit, with eras
# Here the default data/MC for UL and rereco are given (taken based on the release environment)
# If you would switch to AOD, don't forget to add 'isAOD=True' to the defaultArgs!
#
#from EgammaAnalysis.TnPTreeProducer.cmssw_version import isReleaseAbove
#if isReleaseAbove(13,0):

eraPreEE  = '2022preEE'
eraPostEE = '2022postEE'
erapreBPIX  = '2023preBPIX'
erapostBPIX = '2023postBPIX'

submitWrapper("Run2022B_v2", "/EGamma/Run2022B-22Sep2023-v2/MINIAOD", eraPreEE)
# submitWrapper("Run2022C_v1", "/EGamma/Run2022C-22Sep2023-v1/MINIAOD", eraPreEE)
# submitWrapper("Run2022D_v1", "/EGamma/Run2022D-22Sep2023-v1/MINIAOD", eraPreEE)
# # submitWrapper("Run2022E_v1", "/EGamma/Run2022E-22Sep2023-v1/MINIAOD", eraPostEE)
# # submitWrapper("Run2022F_v1", "/EGamma/Run2022F-22Sep2023-v1/MINIAOD", eraPostEE)
# # submitWrapper("Run2022G_v2", "/EGamma/Run2022G-22Sep2023-v2/MINIAOD", eraPostEE)

# submitWrapper('DY_LO_preEE', '/DYto2L-4Jets_MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer22MiniAODv4-130X_mcRun3_2022_realistic_v5-v2/MINIAODSIM', eraPreEE)
# submitWrapper('DY_NLO_preEE', '/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22MiniAODv4-130X_mcRun3_2022_realistic_v5-v2/MINIAODSIM', eraPreEE)
# submitWrapper('DY_LO_postEE', '/DYto2L-4Jets_MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer22EEMiniAODv4-130X_mcRun3_2022_realistic_postEE_v6-v2/MINIAODSIM', eraPostEE)
# submitWrapper('DY_NLO_postEE', '/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22EEMiniAODv4-130X_mcRun3_2022_realistic_postEE_v6-v2/MINIAODSIM', eraPostEE)

# submitWrapper('Run2023C_0v1', '/EGamma0/Run2023C-22Sep2023_v1-v1/MINIAOD', erapreBPIX)
# submitWrapper('Run2023C_0v2', '/EGamma0/Run2023C-22Sep2023_v2-v1/MINIAOD', erapreBPIX)
# submitWrapper('Run2023C_0v3', '/EGamma0/Run2023C-22Sep2023_v3-v1/MINIAOD', erapreBPIX)
# submitWrapper('Run2023C_0v4', '/EGamma0/Run2023C-22Sep2023_v4-v1/MINIAOD', erapreBPIX)
# submitWrapper('Run2023C_1v1', '/EGamma1/Run2023C-22Sep2023_v1-v1/MINIAOD', erapreBPIX)
# submitWrapper('Run2023C_1v2', '/EGamma1/Run2023C-22Sep2023_v2-v1/MINIAOD', erapreBPIX)
# submitWrapper('Run2023C_1v3', '/EGamma1/Run2023C-22Sep2023_v3-v1/MINIAOD', erapreBPIX)
# submitWrapper('Run2023C_1v4', '/EGamma1/Run2023C-22Sep2023_v4-v1/MINIAOD', erapreBPIX)
# submitWrapper('Run2023D_0v1', '/EGamma0/Run2023D-22Sep2023_v1-v1/MINIAOD', erapostBPIX)
# submitWrapper('Run2023D_0v2', '/EGamma0/Run2023D-22Sep2023_v2-v1/MINIAOD', erapostBPIX)
# submitWrapper('Run2023D_1v1', '/EGamma1/Run2023D-22Sep2023_v1-v1/MINIAOD', erapostBPIX)
# submitWrapper('Run2023D_1v2', '/EGamma1/Run2023D-22Sep2023_v2-v1/MINIAOD', erapostBPIX)

# submitWrapper('DY_LO_preBPIX', '/DYto2L-4Jets_MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer23MiniAODv4-130X_mcRun3_2023_realistic_v14-v1/MINIAODSIM', erapreBPIX)
# submitWrapper('DY_NLO_preBPIX', '/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer23MiniAODv4-130X_mcRun3_2023_realistic_v14-v1/MINIAODSIM', erapreBPIX)
# submitWrapper('DY_LO_postBPIX', '/DYto2L-4Jets_MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer23BPixMiniAODv4-130X_mcRun3_2023_realistic_postBPix_v2-v3/MINIAODSIM', erapostBPIX)
# submitWrapper('DY_NLO_postBPIX', '/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer23BPixMiniAODv4-130X_mcRun3_2023_realistic_postBPix_v2-v3/MINIAODSIM', erapostBPIX)

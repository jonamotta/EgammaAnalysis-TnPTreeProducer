#ifndef _MINIADOTRIGGERCANDPRODUCER_H_
#define _MINIADOTRIGGERCANDPRODUCER_H_

#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Framework/interface/one/EDProducer.h"

#include "FWCore/Common/interface/TriggerNames.h"
#include "DataFormats/Common/interface/TriggerResults.h"
#include "DataFormats/HLTReco/interface/TriggerObject.h"
#include "DataFormats/HLTReco/interface/TriggerEvent.h"
#include "DataFormats/HLTReco/interface/TriggerTypeDefs.h"

#include "DataFormats/PatCandidates/interface/TriggerObjectStandAlone.h"
#include "DataFormats/PatCandidates/interface/PackedTriggerPrescales.h"
#include "HLTrigger/HLTcore/interface/HLTConfigProvider.h"

#include "DataFormats/L1Trigger/interface/Tau.h" //for stage 2 L1

#include <DataFormats/Math/interface/deltaR.h>

#include "FWCore/MessageLogger/interface/MessageLogger.h"

#include <string>
#include <vector>

template <class T, class U>
class MiniAODTriggerCandProducer : public edm::one::EDProducer<>{

  typedef std::vector<T> TCollection;
  typedef edm::Ref<TCollection> TRef;
  typedef edm::RefVector<TCollection> TRefVector;

  typedef std::vector<U> UCollection;

public:
  MiniAODTriggerCandProducer(const edm::ParameterSet&);
  ~MiniAODTriggerCandProducer();
  
  void init(const edm::TriggerResults &result, const edm::TriggerNames & triggerNames);
  bool onlineOfflineMatching(TRef ref, 
			     const UCollection* triggerObjects, 
			     std::string filterLabel, float dRmin,const edm::Handle<edm::TriggerResults> & triggerBits,const edm::TriggerNames &triggerNames,edm::Event &iEvent);

  bool onlineOfflineMatchingRECO(TRef ref, 
				 const UCollection* triggerObjects,
				 const trigger::Keys* keys, float dRmin);

  bool L1TauMatching(TRef ref,
                     const std::vector<l1t::Tau>& l1taus,
                     float dRmin);

  bool L1TauMatchingRECO(TRef ref,
                         const std::vector<l1t::Tau>& l1taus,
                         float dRmin);

 private:
  virtual void produce(edm::Event&, const edm::EventSetup&) override;
  
  std::vector<std::string> filterNames_;
  edm::EDGetTokenT<TRefVector> inputs_;
  edm::EDGetTokenT<edm::TriggerResults> triggerBits_;
  edm::EDGetTokenT<trigger::TriggerEvent> triggerEvent_;
  //edm::EDGetTokenT<pat::TriggerObjectStandAloneCollection> triggerObjects_;
  edm::EDGetTokenT<UCollection> triggerObjects_;

  float dRMatch_;
  bool isAND_;
  edm::ParameterSetID triggerNamesID_;
  std::map<std::string, unsigned int> trigger_indices;

  edm::EDGetTokenT<l1t::TauBxCollection> l1tauToken_;
  bool L1TauMatch_;
  float dRMatchL1Tau_;
};

template <class T, class U>
  MiniAODTriggerCandProducer<T, U>::MiniAODTriggerCandProducer(const edm::ParameterSet& iConfig ):
  filterNames_(iConfig.getParameter<std::vector<std::string> >("filterNames")),
    inputs_(consumes<TRefVector>(iConfig.getParameter<edm::InputTag>("inputs"))),
    triggerBits_(consumes<edm::TriggerResults>(iConfig.getParameter<edm::InputTag>("bits"))),
  //triggerObjects_(consumes<pat::TriggerObjectStandAloneCollection>(iConfig.getParameter<edm::InputTag>("objects"))),
    triggerObjects_(consumes<UCollection>(iConfig.getParameter<edm::InputTag>("objects"))),
    dRMatch_(iConfig.getParameter<double>("dR")),
    isAND_(iConfig.getParameter<bool>("isAND")),

    l1tauToken_(consumes<l1t::TauBxCollection> ( iConfig.getParameter<edm::InputTag>("l1tau"))),
    L1TauMatch_(iConfig.getParameter<bool>("L1TauMatch")),
    dRMatchL1Tau_(iConfig.getParameter<double>("dRMatchL1Tau")) {
    
    if(iConfig.existsAs<edm::InputTag>("triggerEvent"))
      triggerEvent_  = mayConsume<trigger::TriggerEvent>(iConfig.getParameter<edm::InputTag>("triggerEvent"));
    produces<TRefVector>();
 }

template <class T, class U>
MiniAODTriggerCandProducer<T, U>::~MiniAODTriggerCandProducer()
{}

template <class T, class U>
  void MiniAODTriggerCandProducer<T, U>::init(const edm::TriggerResults &result, const edm::TriggerNames & triggerNames) {
  
  trigger_indices.clear();
  for (unsigned int i=0; i<triggerNames.triggerNames().size(); i++) {    
    std::string trimmedName = HLTConfigProvider::removeVersion(triggerNames.triggerName(i));
    trigger_indices[trimmedName] = triggerNames.triggerIndex(triggerNames.triggerName(i));    
  }
}

template <class T, class U>
  void MiniAODTriggerCandProducer<T, U>::produce(edm::Event &iEvent, const edm::EventSetup &eventSetup) {
  edm::Handle<edm::TriggerResults> triggerBits;
  //edm::Handle<pat::TriggerObjectStandAloneCollection> triggerObjects;
  edm::Handle<UCollection> triggerObjects;
  
  edm::Handle<TRefVector> inputs;

  iEvent.getByToken(triggerBits_, triggerBits);
  iEvent.getByToken(triggerObjects_, triggerObjects);
  iEvent.getByToken(inputs_, inputs);

  // Create the output collection
  std::unique_ptr<TRefVector> outColRef(new TRefVector);
  
  if (!triggerBits.isValid()) {
    LogDebug("") << "TriggerResults product not found - returning result=false!";
    return;
  }

  const edm::TriggerNames & triggerNames = iEvent.triggerNames(*triggerBits);
  if (triggerNamesID_ != triggerNames.parameterSetID()) {
    triggerNamesID_ = triggerNames.parameterSetID();
    init(*triggerBits, triggerNames);
  } 

  for (size_t i=0; i<inputs->size(); i++) {
    bool saveObj = true;
    TRef ref = (*inputs)[i];
    //std::cout << typeof(triggerObjects.product()) << std::endl;
    if (filterNames_.size() > 0) {
      saveObj = onlineOfflineMatching(ref, triggerObjects.product(), filterNames_[0], dRMatch_,triggerBits,triggerNames,iEvent);
      
      for (size_t f=1; f<filterNames_.size(); f++) {
	if (isAND_)
	  saveObj = (saveObj && onlineOfflineMatching(ref, triggerObjects.product(), filterNames_[f], dRMatch_,triggerBits,triggerNames,iEvent));
	else
	  saveObj = (saveObj || onlineOfflineMatching(ref, triggerObjects.product(), filterNames_[f], dRMatch_,triggerBits,triggerNames,iEvent));
      } 
    }

    if (L1TauMatch_)
    {
      edm::Handle<l1t::TauBxCollection> l1tau_handle;
      iEvent.getByToken(l1tauToken_, l1tau_handle);
      std::vector<l1t::Tau> mergedL1taus;
      for(auto it=l1tau_handle->begin(0); it!=l1tau_handle->end(0); it++){
        mergedL1taus.push_back(*it);
      }

      saveObj = (saveObj && L1TauMatching(ref, mergedL1taus, dRMatchL1Tau_));
    }

    if (saveObj)
      outColRef->push_back(ref);
  }	  

  iEvent.put(std::move(outColRef));
}

//template <class T, class U>
//bool MiniAODTriggerCandProducer<T, U>::onlineOfflineMatching(const edm::TriggerNames & triggerNames, 
//							     //edm::Handle<pat::TriggerObjectStandAloneCollection> triggerObjects, 
//							     TRef ref,
//							     const UCollection* triggerObjects, 
//							     std::string filterLabel, float dRmin) {
//  
//  for (U obj : *triggerObjects) { 
//    obj.unpackPathNames(triggerNames); 
//    if (obj.hasFilterLabel(filterLabel)) {
//      float dR = deltaR(ref->p4(), obj.p4());
//      if (dR < dRmin)
//	return true;
//    }
//  }
//
//  return false;
//}


#endif

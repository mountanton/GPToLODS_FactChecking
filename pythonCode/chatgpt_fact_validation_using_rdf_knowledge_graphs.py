# -*- coding: utf-8 -*-
"""ChatGPT Fact Validation using RDF Knowledge Graphs.ipynb

**1. Import the Libraries**
"""

!pip install SPARQLWrapper
!pip install nltk
!pip install -U sentence-transformers
from SPARQLWrapper import SPARQLWrapper, JSON
from sentence_transformers import SentenceTransformer, util
import numpy as np



# Convert results to JSON format

"""**2. Function for Returning the top-K similar triples**"""

def most_similar(sentences,fullURIs, similarity_matrix,matrix,k):
    if matrix=='Cosine Similarity':
        similar_ix=np.argsort(similarity_matrix[0])[::-1]
    i=0
    retValue=""
    max=0
    #print("The most similar properties of "+fullURIs[0])
    for ix in similar_ix:
        if ix==0:
            continue
        i=i+1
        if i == k+1:
            break
        retValue=retValue+str(similarity_matrix[0][ix])+ '\t'+fullURIs[ix]+" Most Similar Triples\n"
        if(i==1):
            #retValue=fullURIs[ix]
            max=similarity_matrix[0][ix]
        #if(i==2 and "dbpedia" in fullURIs[ix] and similarity_matrix[0][ix]==max):
            #retValue=fullURIs[ix]
    return retValue
        #print (documentsLabels[ix])

"""**3. Importing the wikidata labels for the properties**"""

f = open("wikidata.txt", "r")
wkdProps={}
for x in f:
  prop=x.split(",")[0]
  label=x.split(",")[1].replace("\n","")
  wkdProps[prop]=label
print(wkdProps)

"""**4. Functions for finding the most similar triples by using LODsyndesis**"""

# A GET request to the API
import re

def getBestPredicate(entity,property,fullProperty):
    url = "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/allFacts?uri="+entity
    sentences = [re.sub( '(?<!^)(?=[A-Z])', ' ',property).lower()]
    response =requests.get(url, 
                    headers={'Accept': 'application/json'})
    response_json = response.json()
   
    fullURIs=[fullProperty]
    #print(response_json)
    for hit in response_json:
      if(hit["predicate"]!='<http://www.w3.org/2002/07/owl#sameAs>' and hit["predicate"]!='<http://www.w3.org/2002/07/owl#equivalentClass>'):
          if(hit["predicate"]=='<http://www.w3.org/2002/07/owl#equivalentProperty>'):
              pred1 = hit["subject"].replace("<","").replace(">","")
              pred2 = hit["object"].replace("<","").replace(">","")
              pred1Split=pred1.split("/")
              pred2Split=pred1.split("/")
              if(not pred1 in fullURIs):
                sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1Split[len(pred1Split)-1]).lower())
                fullURIs.append(pred1)
              if(not pred2 in fullURIs):
                sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred2Split[len(pred2Split)-1]).lower())
                fullURIs.append(pred2)
          else:
            pred1 = hit["predicate"].replace("<","").replace(">","")
            pred1Split=pred1.split("/")
            if(not pred1 in fullURIs):
              sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1Split[len(pred1Split)-1]).lower())
              fullURIs.append(pred1)

    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    embeddings = model.encode(sentences)
    pairwise_similarities=np.dot(embeddings,embeddings.T)
    retValue=most_similar(sentences,fullURIs,pairwise_similarities,'Cosine Similarity',5)
    return retValue

currentEntity=""
sentences=[""]
fullURIs=[""]
def getBestPredicateObject(entity,property,fullProperty,object,fullObject,topK):
    global currentEntity
    global sentences
    global fullURIs
    sentences[0] = re.sub( '(?<!^)(?=[A-Z])', ' ',property).lower()+ " "+re.sub( '(?<!^)(?=[A-Z])', ' ',object).lower()
    fullURIs[0]=fullProperty+" "+fullObject
    if(currentEntity!=entity or len(sentences)==1):
      url = "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/allFacts?uri="+entity
      try:
        response =requests.get(url, 
                      headers={'Accept': 'application/json'})
        response.raise_for_status()
      except requests.exceptions.HTTPError:
         response_json = []
      else:
         response_json = response.json()  

     # response_json = response.json()  
      currentEntity=entity
      #print(response_json)
      for hit in response_json:
        if(hit["predicate"]!='<http://www.w3.org/2002/07/owl#sameAs>' and hit["predicate"]!='<http://www.w3.org/2002/07/owl#equivalentClass>'):
            if(hit["predicate"]!='<http://www.w3.org/2002/07/owl#equivalentProperty>'):
              pred1 = hit["predicate"].replace("<","").replace(">","")
              obj1=hit["object"].replace("<","").replace(">","").replace("_"," ")
              pred1Split=pred1.split("/") 
              if(hit["object"].replace("<","").replace(">","")==entity):
                obj1=hit["subject"].replace("<","").replace(">","").replace("_"," ")
              obj1Split=obj1.split("/")
              pred1SplitCell=pred1Split[len(pred1Split)-1].split('#') # to add
              if("http://www.wikidata.org/entity/" in pred1):
                wkdPred=pred1.replace("http://www.wikidata.org/entity/","").replace("c","").replace("*","")
                wkdPredicate=wkdPred
                if(wkdPred in wkdProps):
                  wkdPredicate=str(wkdProps[wkdPred])
                  #print(wkdPredicate)
                sentences.append(wkdPredicate+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',obj1Split[len(obj1Split)-1]).lower())
                fullURIs.append(pred1+ " "+hit["object"].replace("<","").replace(">","")+ " "+hit["provenance"])
              else:
                sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1SplitCell[len(pred1SplitCell)-1]).lower()+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',obj1Split[len(obj1Split)-1]).lower())
                fullURIs.append(pred1+ " "+hit["object"].replace("<","").replace(">","")+ " "+hit["provenance"])
      response =getAllDBpediaTriples("<"+entity+">")
      currentEntity=entity
      #print(response_json)
      for hit in response["results"]["bindings"]:
        if(hit["predicate"]["value"]!='http://www.w3.org/2002/07/owl#sameAs' and hit["predicate"]["value"]!='http://www.w3.org/2002/07/owl#equivalentClass'):
            if(hit["predicate"]["value"]!='<http://www.w3.org/2002/07/owl#equivalentProperty>'):
              pred1 = hit["predicate"]["value"].replace("<","").replace(">","")
              if(hit["object"]["type"]=="literal" and "xml:lang" in hit["object"].keys() and hit["object"]["xml:lang"]!="en"):
               continue
              obj1=hit["object"]["value"].replace("<","").replace(">","").replace("_"," ")
              pred1Split=pred1.split("/") 
              obj1Split=obj1.split("/")
              pred1SplitCell=pred1Split[len(pred1Split)-1].split('#') # to add
              sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1SplitCell[len(pred1SplitCell)-1]).lower()+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',obj1Split[len(obj1Split)-1]).lower())
              fullURIs.append(pred1+ " "+hit["object"]["value"].replace("<","").replace(">","")+ " <http://dbpedia.org/current>")
    
    else:
       print(currentEntity)
    

    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    #print(sentences)
    embeddings = model.encode(sentences)
    pairwise_similarities=np.dot(embeddings,embeddings.T)
    retValue=most_similar(sentences,fullURIs,pairwise_similarities,'Cosine Similarity',topK)
    return retValue

# Print the response

"""**5. Functions for finding the most similar triples by using DBpedia Only**"""

import json 

def checkDBpedia(entity,predicate,obj):
  # Specify the DBPedia endpoint
  sparql = SPARQLWrapper("http://dbpedia.org/sparql")
  # Query for the description of "Capsaicin", filtered by language
  sparql.setQuery("ASK WHERE { {"+entity+" "+predicate+" "+obj+"}}")
  sparql.setReturnFormat(JSON)
  result = sparql.query().convert()
  results=""
  dictionary=[]
  i=0
  # The return data contains "bindings" (a list of dictionaries)
  if(result["boolean"]==True):
      # We want the "value" attribute of the "comment" field
      dictionary.append({ 
      "predicate": predicate, 
      "provenance": '<http://dbpedia.org/current>', 
      "subject": entity,
      "object": obj,
      "threshold": "1.0"
     })
  if(dictionary==[]):
    sparql.setQuery("SELECT  ?predicate WHERE { {"+entity+" ?predicate "+ obj+"} UNION {"+obj+ "?predicate " +entity+" } . filter(!regex(?predicate,'wiki'))}")
    if('"' in obj ):
       sparql.setQuery("SELECT  ?predicate WHERE { "+entity+" ?predicate "+ obj+" . filter(!regex(?predicate,'wiki'))}")
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()
   # print(result)
    for hit in result["results"]["bindings"]:
      # We want the "value" attribute of the "comment" field
       dictionary.append({ 
      "predicate": '<'+hit["predicate"]["value"]+'>', 
      "provenance": '<http://dbpedia.org/current>', 
      "subject": entity,
      "object": obj,
      "threshold": "0.5"
     })
  if(dictionary==[]):
    sparql.setQuery("SELECT  ?obj WHERE { {"+entity+" "+predicate+" ?obj} UNION {?obj "+predicate+ " " +entity+" }}")
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()
  #  print(result)
    for hit in result["results"]["bindings"]:
      objNew=hit["obj"]["value"]
      if "http" in objNew:
          objNew="<"+objNew+">"
      dictionary.append({ 
      "predicate": predicate, 
      "provenance": '<http://dbpedia.org/current>', 
      "subject": entity,
      "object": objNew,
      "threshold": "0.5"
     })
  #if(dictionary==[]):
    sparql.setQuery("SELECT  ?obj WHERE { {"+entity+" "+predicate.replace("http://dbpedia.org/ontology/","http://dbpedia.org/property/")+" ?obj} UNION {?obj "+predicate.replace("http://dbpedia.org/ontology/","http://dbpedia.org/property/")+ " " +entity+" }}")
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()
   # print(result)
    for hit in result["results"]["bindings"]:
      objNew=hit["obj"]["value"]
      if "http" in objNew:
        objNew="<"+objNew+">"
      # We want the "value" attribute of the "comment" field
      dictionary.append({ 
      "predicate": predicate.replace("http://dbpedia.org/ontology/","http://dbpedia.org/property/"), 
      "provenance": '<http://dbpedia.org/current>', 
      "subject": entity,
      "object": objNew,
      "threshold": "0.5"
     })
  return dictionary
#checkDBpedia("<http://dbpedia.org/resource/Aristotle>","<http://dbpedia.org/ontology/birthPlace>","<http://dbpedia.org/resource/Stagira_(ancient_city)>")

def getAllDBpediaTriples(entity):
  sparql = SPARQLWrapper("http://dbpedia.org/sparql")
  # Query for the description of "Capsaicin", filtered by language
  sparql.setQuery("SELECT * WHERE { {"+entity+" ?predicate ?object } UNION {?object ?predicate " +entity+" }. filter(!regex(?predicate,'wiki'))}")
  sparql.setReturnFormat(JSON)
  result = sparql.query().convert()
  return result
#print(getAllDBpediaTriples("<http://dbpedia.org/resource/Nikos_Zisis>"))

def getBestPredicateObjectDBpedia(entity,property,fullProperty,object,fullObject,topK):
    global currentEntity
    global sentences
    global fullURIs
    sentences[0] = re.sub( '(?<!^)(?=[A-Z])', ' ',property).lower()+ " "+re.sub( '(?<!^)(?=[A-Z])', ' ',object).lower()
    fullURIs[0]=fullProperty+" "+fullObject
    if(currentEntity!=entity or len(sentences)==1):
      response =getAllDBpediaTriples(entity)
      currentEntity=entity
      #print(response_json)
      for hit in response["results"]["bindings"]:
        if(hit["predicate"]["value"]!='http://www.w3.org/2002/07/owl#sameAs' and hit["predicate"]["value"]!='http://www.w3.org/2002/07/owl#equivalentClass'):
            if(hit["predicate"]["value"]!='<http://www.w3.org/2002/07/owl#equivalentProperty>'):
              pred1 = hit["predicate"]["value"].replace("<","").replace(">","")
              if(hit["object"]["type"]=="literal" and "xml:lang" in hit["object"].keys() and hit["object"]["xml:lang"]!="en"):
               continue
              obj1=hit["object"]["value"].replace("<","").replace(">","").replace("_"," ")
              pred1Split=pred1.split("/") 
              obj1Split=obj1.split("/")
              pred1SplitCell=pred1Split[len(pred1Split)-1].split('#') # to add
              sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1SplitCell[len(pred1SplitCell)-1]).lower()+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',obj1Split[len(obj1Split)-1]).lower())
              fullURIs.append(pred1+ " "+hit["object"]["value"].replace("<","").replace(">",""))
    else:
       print(currentEntity)
    
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    #print(sentences)
    embeddings = model.encode(sentences)
    pairwise_similarities=np.dot(embeddings,embeddings.T)
    retValue=most_similar(sentences,fullURIs,pairwise_similarities,'Cosine Similarity',topK)
    return retValue

"""**6. Calculate Similarity for the Candidates**"""

def calculateSimilarity(pred1, obj1,pred2, obj2):
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    newPred1=pred1.replace(">","").replace('_',' ').split("/")
    newObj1=obj1.replace(">","").replace('"','').replace('_','').split("/")
    sentence1= re.sub( '(?<!^)(?=[A-Z])', ' ',newPred1[len(newPred1)-1]).lower()+ " "+re.sub( '(?<!^)(?=[A-Z])', ' ',newObj1[len(newObj1)-1]).lower()
    #print(pred2)
    if("http://www.wikidata.org/entity/" in pred2):
        wkdPred=pred2.replace("http://www.wikidata.org/entity/","").replace("c","").replace("*","").replace(">","").replace("<","")
        wkdPredicate=wkdPred
        if(wkdPred in wkdProps):
          wkdPredicate=str(wkdProps[wkdPred])
          #print(wkdPredicate)
        newObj2=obj2.replace(">","").replace('_',' ').replace('"','').split("/")
        sentence2= wkdPredicate+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',newObj2[len(newObj2)-1]).lower()
    else:
      newPred2=pred2.replace(">","").replace('_',' ').split("/")
      newObj2=obj2.replace(">","").replace('_',' ').replace('"','').split("/")
      sentence2= re.sub( '(?<!^)(?=[A-Z])', ' ',newPred2[len(newPred2)-1]).lower()+ " "+re.sub( '(?<!^)(?=[A-Z])', ' ',newObj2[len(newObj2)-1]).lower()
    #print(sentence1, sentence2)
    sentencesBoth=[sentence1,sentence2]
    embeddings = model.encode(sentencesBoth)
    pairwise_similarities=np.dot(embeddings,embeddings.T)
    return str(pairwise_similarities[0][1])

def sortSimilarities(sentences,topK):
    sentencesSplit=sentences.split("\n")
    key_value = {}
    cnt=0
    for entry in sentencesSplit:
      entrySplit=entry.split("\t")
      if len(entrySplit)==2:
        threshold=entrySplit[0]
        triple=entrySplit[1]
        key_value[threshold]=triple
        #print(threshold)
        #print(triple)
    for i in sorted(key_value.keys(),reverse=True):
        print(i,key_value[i] )
        cnt=cnt+1
        if(cnt==topK):
          break

"""**7. The process of validating the facts. You need to configure the path containing the CHATGPT triples, if DBpedia will be used alone or not and the number of K (for the most similar)**"""

import requests
import time

factsGPT="greekPersons.nt"
dbpediaOnly=False #onlyDBpediaValue
topK=3 #topKValue
#triplesChecker(factsGPT,True,3)

#def triplesChecker(factsGPT,onlyDBpediaValue,topKValue):
tripleID=1
correctCount=0
samePredicateOrObjectCount=0
bestMatchCount=0
retValue=""
currentEntity=""
response_json=[]
sentences=[""]
fullURIs=[""]

factsSplit = open(factsGPT, "r")
#factsSplit=factsGPT.split("\n")
for fct in factsSplit:
  start = time.time()
  factSplit=fct.split("> ")
  dbpediaTriples=[]
  if(len(factSplit)>=3):
    entity=factSplit[0].split("<")[1]
    predicateSplit=factSplit[1].replace("<","").split("#")
    predicate=predicateSplit[len(predicateSplit)-1]
    obj=factSplit[2].replace("<","").replace('"',"").replace(" .","").split("^^")
    if(obj[0].isnumeric()):
      obj[0]='"'+obj[0]+'"'
    facts=predicate+ " "+obj[0]
    
    if "http" in factSplit[2].split("^^")[0]:
      dbpediaTriples=checkDBpedia("<"+entity+">",factSplit[1]+">",factSplit[2].replace(" .","").split("^^")[0]+">")
    else:
      dbpediaTriples=checkDBpedia("<"+entity+">",factSplit[1]+">",factSplit[2].replace(" .","").split("^^")[0])
    if(dbpediaOnly==False):
      url = "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/factChecking?uri="+entity+"&fact="+facts+"&threshold=0.5"
      # A GET request to the API
      response =requests.get(url, 
                      headers={'Accept': 'application/json'})
      
  else:
    continue
# Print the response
  if dbpediaOnly==False:
      response_json = response.json()
  else:
      response_json = []
  if(response_json==[] and "http://dbpedia.org/ontology/" in facts and dbpediaOnly==False):
    url = "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/factChecking?uri="+entity+"&fact="+facts.replace("http://dbpedia.org/ontology/","http://dbpedia.org/property/")+"&threshold=0.5"
    #print(url)
    # A GET request to the API
    response =requests.get(url, 
                    headers={'Accept': 'application/json'})
    response_json = response.json()

  correct=""
  samePredicateOrObject=""
  bestMatch=""
  if(entity!=currentEntity):
    sentences=[""]
    fullURIs=[""]

  #print(dbpediaTriples)
  response_json.extend(dbpediaTriples)
  #print(response_json)
  # print(response_json)
  if(response_json==[]):
    newPred=predicate.split("/")
    newObj=obj[0].split("/")
    #print(entity,newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0])
    if(dbpediaOnly==False):
      bestPredicate=  getBestPredicateObject(entity,newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0],topK) # getBestPredicateObjectDBpedia("<"+entity+">",newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0],topK) # #getBestPredicate(entity,newPred[len(newPred)-1],predicate) 
      retValue=str(bestPredicate)
    else:
      bestPredicate= getBestPredicateObjectDBpedia("<"+entity+">",newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0],topK)  # getBestPredicateObjectDBpedia("<"+entity+">",newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0],topK) # #getBestPredicate(entity,newPred[len(newPred)-1],predicate) 
      retValue=str(bestPredicate)
  else:
    for entry in response_json:
      if entry["threshold"]=="1.0":
        correct=entry["threshold"]+"\t"+entry["subject"]+ " "+entry["predicate"]+" "+entry["object"]+" "+ entry["provenance"]+" Same Triple\n"
      else:
        if("<"+predicate.replace("property","ontology")+">"==entry["predicate"].replace("property","ontology") and obj[0].replace('"',"").replace("<","").replace(">","").lower()==entry["object"].replace('"',"").replace("<","").replace(">","").lower()):
            correct="1.0\t"+entry["subject"]+ " "+entry["predicate"]+" "+entry["object"]+" "+ entry["provenance"]+" Same Triple\n"
        elif("<"+predicate.replace("property","ontology")+">"==entry["predicate"].replace("property","ontology") or entry["predicate"]=="<http://www.w3.org/2006/vcard/ns#type>"):
            similarity=calculateSimilarity(predicate,obj[0],entry["predicate"],entry["object"])
            samePredicateOrObject+=similarity+"\t"+entry["subject"]+ " "+entry["predicate"]+" "+entry["object"]+" "+ entry["provenance"]+" Same Predicate - Different Object\n"
        elif(obj[0].replace('"',"").replace("<","").replace(">","").lower()==entry["object"].replace('"',"").replace("<","").replace(">","").lower()):
          similarity=calculateSimilarity(predicate,obj[0],entry["predicate"],entry["object"])
          samePredicateOrObject+=similarity+"\t"+entry["subject"]+ " "+entry["predicate"]+" "+entry["object"]+" "+ entry["provenance"]+" Same Object - Different Predicate\n"
        else:
          similarity=calculateSimilarity(predicate,obj[0],entry["predicate"],entry["object"])
          bestMatch+=similarity+"\t"+entry["subject"]+ " "+entry["predicate"]+" "+entry["object"]+" "+ entry["provenance"]+" Most Similar Triples\n"
  print("#"+str(tripleID)+" "+" ChatGPT Triple: "+fct)
  tripleID=tripleID+1
  print("Fact Checking Triple(s) and Provenance")
  if(correct!=""):
    print(correct)
    correctCount=correctCount+1
  #elif(sameObject!=""):
  # print(sameObject)
  #  sortSimilarities(sameObject,topK)
  # sameObjectCount=sameObjectCount+1
  elif(samePredicateOrObject!=""):
    #print(samePredicate)
    sortSimilarities(samePredicateOrObject,topK)
    samePredicateOrObjectCount=samePredicateOrObjectCount+1
  elif(bestMatch!=""):
    sortSimilarities(bestMatch,topK)
    #print(bestMatch)
    bestMatchCount=bestMatchCount+1
  else:
    print(retValue)
    bestMatchCount=bestMatchCount+1


  end = time.time()
  print("ElapsedTime: ",end - start)
  print("\n")
print("A. Same or Equivalent:" +str(correctCount))
print("B. Same Predicate or Object:" +str(samePredicateOrObjectCount))
print("C. Most SImilar Triple(s):" +str(bestMatchCount))

"""**Appendix Code. Additional Code for checking availability of URIs/properties in DBpedia**"""

def checkURIExistence(URIs,isProperty):
  for entity in URIs:
      sparql = SPARQLWrapper("http://dbpedia.org/sparql")
      # Query for the description of "Capsaicin", filtered by language
      sparql.setQuery("ASK WHERE { {"+entity+" ?p ?o} UNION {?o ?p "+entity+"}}")
      if(isProperty):
         sparql.setQuery("ASK WHERE { {?s "+entity+"  ?o}}")
      sparql.setReturnFormat(JSON)
      result = sparql.query().convert()
      #print(result)
      results=""
      dictionary=[]
      i=0
      # The return data contains "bindings" (a list of dictionaries)
      if(result["boolean"]==True):
        print(entity+" exists")
      else:
         print(entity+" notAvailable")
URIs=[]
Properties=[]


factsGPT="greekPersons.nt"
factsSplit = open(factsGPT, "r")
for x in factsSplit:
  factSplit=x.split("> ")
  dbpediaTriples=[]
  if(len(factSplit)>=3):
    predicate=factSplit[1]+">"
    if(predicate in Properties):
      i=0
    else:
      Properties.append(predicate)
    subject=factSplit[0]+">"
    if(subject in URIs):
      i=0
    else:
      URIs.append(subject)
    obj=factSplit[2].replace(" .","").split("^^")[0]+">"
    if "<" in obj:
       if(obj in URIs):
         i=0
       else:
         URIs.append(obj)
   
print("Properties\n")
checkURIExistence(Properties,True)
print("\n\nResources\n")
checkURIExistence(URIs,False)

"""**Appendix Code for implementing the pipelines**"""

#!pip install openai
import openai

# Define OpenAI API key 
openai.api_key = "x"

# Set up the model and prompt
model_engine = "text-davinci-003"
#prompt = "find me all the entities and their DBpedia links from the following text: The Godfather is an American crime film directed by Francis Ford Coppola and produced by Albert S. Ruddy, based on Mario Puzo's best-selling novel of the same name. The film features an ensemble cast including Marlon Brando, Al Pacino, James Caan, Richard Castellano, Robert Duvall, Sterling Hayden, John Marley, Richard Conte, and Diane Keaton. The story, spanning from 1945 to 1955, chronicles the Corleone crime family under patriarch Vito Corleone (Brando), focusing on the transformation of one of his sons, Michael Corleone (Pacino), from reluctant family outsider to ruthless mafia boss."
prompt="give me 5 RDF N-triples using DBpedia format for El Greco"
# Generate a response
completion = openai.Completion.create(
    engine=model_engine,
    prompt=prompt,
    max_tokens=1024,
    n=1,
    stop=None,
    temperature=0.5,
)

factsGPT=completion.choices[0].text
print(factsGPT)
triplesChecker(factsGPT,True,3)

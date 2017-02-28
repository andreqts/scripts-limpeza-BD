#!/usr/bin/python
# coding=cp1252
# -*- coding: cp1252 -*-

sep = ',' #separador usado para o CSV (TODO: permitir customização)

import locale
locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
import sys
          
DEFAULT_OUTPUT = 'corrected.csv'

def main(args):
  if len(args) < 3: #precisa no mínimo 3 parâmetros (o primeiro é o executável,
                    #seguindo o mesmo padrão do main do ANSI C)
    print('\nusage:  "%s" <catalogue file path> <input csv file> [output csv file]' % args[0])
    print('\ndefault output = "%s"' % DEFAULT_OUTPUT)
    exit() #imprime dica de como usar e aborta
  
  # se houver o quarto argumento (terceiro fornecido pelo usuário) usa ele,
  # senão usa o default  
  global fout
  fout = (DEFAULT_OUTPUT if (len(args) == 3) else args[3])
  
  global fin
  global fcat
  fin, fcat = args[1:3]

if __name__ == "__main__":
    main(sys.argv)

import re, collections

# Recebe o texto completo em text, e retorna lista de entradas (considerando
# uma entrada por linha do arquivo fin ou fcat). As entradas são convertidas
# para minúsculas, a fim de abstrair o 'case' das entradas.
# Entradas em cada linha podem conter número inteiro após vírgula, funcionando
# como 'pontuações' para itens de catálogo (quanto maior mais terão priordade)
#  PARAMETROS
#    text - texto de arquivo de entrada com 1 palavra por linha, opcionalmente
#           seguidas de vírgula e número inteiro (pontoações de catálogo)
#  RETORNO
#    lista de palavras válidas do catálogo, ou lista de listas do tipo:
#    [<PALAVRA VÁLIDA>, <PONTUAÇÃO>]
def words(text):
  lines = ((text.lower()).split('\n')) # cria lista com as linhas
  return [line.split(sep) for line in lines] #retorna lista de listas de
                                             #até 2 itens(palavra, pontuações)
  #NOTA: note que o método split da lista, se não encontrar 'sep', retorna
  #      lista com 1 só elemento. Em todo o caso terminamos com lista de listas.

# In[2]:
    
#TODO: modificar para carregar pontoações
def train(catalogo):
    ''' Essa função 'treina' o nosso modelo, a partir das entradas do catálogo '''
    model = collections.defaultdict(lambda: 1)
    for f in catalogo:
        key = (f[0].strip()).lower()
        if key == '':
            continue #entrada vazia (linha em branco) - segue o baile...
        if (len(f) > 1): #tem pontoação?
            model[key] += int(f[1]) #soma (podem haver mais entradas iguais)
        else:
            model[key] += 1 #note que, como é defaultdict, não precisa testar
                            #se a entrada já existe antes de incrementar.
                            #Se fosse dict normal teria que testar.
    return model

alphabet = 'abcdefghijklmnopqrstuvwxyzáàãéêíóõôúç'

#Esta função calcula as diversas variações possíveis de erros de digitação
#de uma determinada palavra.
#  PARAMETROS
#    word: palavra correta do catálogo.
#  RETORNO
#    Set com conjunto de palavras possíveis de serem geradas com 1 único nível
#    de alteração (modificação) da palavra original do catálogo (word).
def edits1(word):
   #splits lista as possibilidades de divisões em dois da palavra (usado a seguir)
   splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
   #deletes lista as possibilidades de erros de omissão de 1 letra
   deletes    = [a + b[1:] for a, b in splits if b]
   #transposes lista combinações geradas por trocas de 2 letras consecutivas
   transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b)>1]
   #replaces lista erros por trocas de 1 letra por alguma outra do alfabeto
   replaces   = [a + c + b[1:] for a, b in splits for c in alphabet if b]
   #inserts lista as combinações geradas por inserções de 1 letra aleatória do
   #alfabeto no meio da palavra
   inserts    = [a + c + b     for a, b in splits for c in alphabet]
   #retorna objeto set (elimina repetições)
   return set(deletes + transposes + replaces + inserts)

def known_edits2(word):
    return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in NWORDS)

#retorna conjunto de palavras 'conhecidas' de words (ou seja, que existem no 
#catalogo)
def known(words): return set(w for w in words if w in NWORDS)

#def correct(word):
#    candidates = known([word]) or known(edits1(word)) or known_edits2(word) or [word]
#    return max(candidates, key=NWORDS.get)

#correct('cal')

import codecs

def correct(word):
    #candidates = known([word]) or known(edits1(word)) or known_edits2(word) #TODO:?
    
    # se houver candidados de primeiro nível, fica com resultado de known(edits1(words))
    # porém se este retornar vazio, testa a cláusula depois do or (known_edits2)
    return known(edits1(word)) or known_edits2(word)

    #print("candidates = " + str(candidates))
    #return candidates
    
def show_progress(prog):
    assert(prog >= 0.0 and prog <= 100.0)
    str = '|'
    mlstep = 10.0
    assert(mlstep <= 100.00)
    ml = mlstep
    for i in range(0, int(100 / mlstep)):
        if prog >= ml:
            str += '#'
            ml += mlstep
        else:
            str += '-'
    str += '|'
    print('Progress: %s [%.3f%%]' % (str, prog))
    
def get_file_size(path):
    import os
    statinfo = os.stat(path)
    return statinfo.st_size

    
def analyze(fcat, fin, fout):
    #'treina' nosso modelo a partir do catálogo, e guarda modelo resultante no
    #defaultdict NWORDS, que conterá uma lista de listas do tipo:
    #    [<ENTRADA DO CATÁLOGO>, <PONTOAÇÃO>]
    # A pontoação (ou pontuação, tanto faz) é usada como critério de prioridade.
    NWORDS = train(words((file(fcat).read())))

    dictAnalyzed = {}
    KnownList = collections.defaultdict(lambda: 0)
    UnmatchedList = collections.defaultdict(lambda: 0)
        
    finsize = get_file_size(fin)
    next_milestone = 0
    milestone_step = finsize / 10000.0
    pos = 0

    nknown = 0 # numero de palavras conhecidas, considerando repeticoes
    ncorrectable = 0 # numero de palavras corrigiveis, considerando tb. repetidas
    nunknown = 0 # numero de palavras desconhecidas, sem sugestoes de correcao

    import csv
    ffin = open(fin, 'rb')
    arq = csv.reader(ffin, delimiter = sep)
    ffout = open(fout, 'w') #TODOAQ:
    import operator
    inwords_cnt = 0
    for cityraw in ffin:
        inwords_cnt += 1
        pos += len(cityraw)
        if pos > next_milestone:
            show_progress((pos * 100.0) / finsize)
            next_milestone += milestone_step
        city = cityraw.lower().strip()
        if (city in NWORDS):
            nknown += 1
            KnownList[city] += 1
            #ffout.write('\r\n' + city + ';')
        elif dictAnalyzed.get(city) != None:
            #ffout.write('\r\n' + city + '; ' + str(dictAnalyzed.get(city)))
            ncorrectable += 1
            sorted_cand = dictAnalyzed.get(city)
            sorted_cand[-1] += 1
            dictAnalyzed[city] = sorted_cand
        else:
            candidates = correct(city) #TODO:    
            if (len(candidates) > 0):
                ncorrectable += 1
                sorted_cand = sorted(candidates, key=NWORDS.get, reverse=True)
                sorted_cand.append(1)
            else:
                citystrip = cityraw.strip()
                UnmatchedList[citystrip] = UnmatchedList[citystrip] + 1
                nunknown += 1

    ffout.write('SUMMARY:\n  - {:d} words analyzed\n  - {:d} were known\n  - {:d} were unknown but correctable\n  - {:d} are unknown and not correctible\n\n'.format(inwords_cnt, nknown, ncorrectable, nunknown))

    ffout.write('\nKNOWN WORDS\n')
    ffout.write('-------------------------------------------\n')
    ffout.write('WORD,COUNT\n')
    ffout.write('-------------------------------------------\n')
    for ww in KnownList:
        ffout.write('{:s},{:d}\n'.format(ww,KnownList[ww]))

    ffout.write('\nCORRECTABLE WORDS\n')
    ffout.write('-------------------------------------------\n')
    ffout.write('WORD,CANDIDATE1,CANDIDATE2,...,COUNT\n')
    ffout.write('-------------------------------------------\n')
    for ww in dictAnalyzed:
        ffout.write('{:s},'.format(ww))
        for i, wrds in enumerate(dictAnalyzed[ww]):
            #print('%d--%s[%d]' % (i, wrds, len(dictAnalyzed[ww])))#TODOAQ
            if i < (len(dictAnalyzed[ww]) - 1):
                ffout.write('{:s},'.format(wrds)) # imprime candidatas, uma a uma
            else:
                ffout.write('{:d},'.format(wrds)) # imprime pontoação por ocorrências
        ffout.write('\n')
      
    ffout.write('\nNOT CORRECTABLE WORDS\n')
    ffout.write('-------------------------------------------\n')
    ffout.write('WORD,\n')
    ffout.write('-------------------------------------------\n')
    for ww in UnmatchedList:
        ffout.write('{},{}\n'.format(ww,UnmatchedList[ww]))

    ffout.close() 

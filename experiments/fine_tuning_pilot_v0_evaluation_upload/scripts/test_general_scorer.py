from general_scorer import score_output
def c(t,g,r):return {'gold':g,'scoring_rubric':{'type':t,'forbidden_extra_text':True}}
def main():
 tests=[(score_output('{"a":1}',c('json_exact',{'a':1},{}))[1],1),(score_output('Answer: {"a":1}',c('json_exact',{'a':1},{}))[1],0),(score_output('2',c('integer_exact','2',{}))[1],1),(score_output('02',c('integer_exact','2',{}))[1],0),(score_output(' A  B ',c('normalized_string_exact','A B',{}))[1],1),(score_output('2/4',c('reduced_fraction_exact','1/2',{}))[1],0),(score_output('ABCDE',c('string_exact','ABCDE',{}))[1],1)]
 code={'gold':{'tests':[{'input':['abc'],'output':'cba'}]},'scoring_rubric':{'type':'python_unit_tests'}}
 tests += [(score_output('def solve(s):\n return s[::-1]',code)[1],1),(score_output('def solve(s):\n return s',code)[1],0),(score_output('import os\ndef solve(s): return s',code)[1],0),(score_output('def solve(:',code)[1],0),(score_output('def solve(s):\n while True: pass',code)[1],0)]
 assert all(a==b for a,b in tests),tests;print('GENERAL_SCORER_UNIT_TESTS_PASS')
if __name__=='__main__':main()

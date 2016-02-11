from subprocess import Popen,STDOUT,PIPE
import sys
import os
import pexpect
from getpass import getuser as username,getpass
from loglib import log


def catch(f):

    def wrapper(self,*args):
        
        try:
            f(self,*args)
        except Exception as e:
            log.error('Exception happened!!! %s',e)
    return wrapper


class Cmd_Exec:


    def execute(self,command,write_in_file=""):
            
            
            if write_in_file != PIPE:
                
                if write_in_file.closed:                    
                    log.error('file %s is not open for reading/writing' % write_in_file)    
                    sys.exit(3)

                else:
                    p = Popen(command,shell=True,stdout=write_in_file,stderr=STDOUT)        
                    self.stdOut,self.stdErr = p.communicate()

            else:
                p = Popen(command,shell=True,stdout=write_in_file,stderr=STDOUT)
                self.stdOut,self.stdErr = p.communicate()
            

class Custom_Command(Cmd_Exec):

    @catch
    def run(self,cmd,file_=PIPE):
        self.execute(cmd,file_)



class Git(Cmd_Exec):

    def __init__(self):
        pass
        
    @catch
    def add(self,files=[],infile=PIPE):
        self.execute('git add '+' '.join(files),infile)

    @catch
    def rebase(self,infile=PIPE):
        self.execute('git rebase',infile)
        
    @catch
    def show_branches(self,infile=PIPE):
        self.execute('git branch',infile)
        
    @catch
    def commit(self,message="",infile=PIPE):
        self.execute('git commit -m '+"'"+message+"'",infile)


    @catch
    def checkout(self,branch="",infile=PIPE):
        self.execute('git checkout '+branch,infile)

    @catch
    def diff(self,infile=PIPE):
        self.execute('git diff',infile)

    @catch
    def log(self,file_to_follow="",infile=PIPE):
        self.execute('git log '+file_to_follow+'|head -n2',infile)


    @catch
    def reset(self,mode='soft',times=None,infile=PIPE):
        self.execute('git reset --'+mode+' HEAD~'+str(times),infile) 


    @catch
    def stash(self,arg='',infile=PIPE):
        self.execute('git stash '+arg,infile)


def git_rebase(branch):

#:begin git svn rebase :#
    gitobj=Git()
    global password 
    password = getpass('Password for svn:')
    print 'Requested: ',branch
    log.info('Requested:%s ',branch)
    gitobj.checkout(branch)
    print 'Switched to %s.Proceed to rebase' % branch
    log.info('Switched to %s.Proceed to rebase' % branch)
    child = pexpect.spawn('git svn rebase')
    child.expect(username()+"@svne1.access.nokiasiemensnetworks.com's password:")
    child.sendline(password)
    child.expect(pexpect.EOF,timeout=None)
    child.terminate()
    print 'Done\n'
    log.info('Done\n')


def git_dcommit():

    
    print 'Preparing to commit in svn'
    log.info('Preparing to commit in svn')
    print '=========================='
    c = pexpect.spawn('git svn dcommit')
    c.expect(username()+"@svne1.access.nokiasiemensnetworks.com's password:")
    c.sendline(password)
    c.expect(pexpect.EOF,timeout=None)
    c.terminate()
    print 'Commited!\n'
    log.info('Commited!')
    print '==========================='
    print 'Done\n'
 

def git_stash_list(starting_point):


    g = Git()
    print 'Show how is the stash before any further proceeding'
    g.stash('list')
    print 'Stash before: \n',g.stdOut
    log.info('Stash before:\n%s' % g.stdOut)
    print '\n\n'
    log.info('\n\n')

    print 'Stash your local changes if any @%s' % starting_point
    log.info('Stash your local changes if any @%s' % starting_point)
    g.stash()
    print 'Stash is done\n'
    log.info('Stash is done\n')
        
    print 'Show how is the stash after'
    log.info('Show how the stash is after stash')
    g.stash('list')
    print 'Stash after:\n ',g.stdOut
    log.info('Stash after:\n%s' % g.stdOut)
    print '\n\n'
    log.info('\n\n')

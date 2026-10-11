"""Musical Cartesian-product graph and structured unitary evolution.
Vertices encode actual three-interval gestures, four-attack rhythms and chords.
No arbitrary physical-coordinate bins or full-system dense operators.
"""
import itertools,time
import numpy as np

INTERVALS=np.array([-2,-1,1,2])
SHAPE=(4,4,4,16,8)
def hermitian_unitary(h,t):
    e,v=np.linalg.eigh(h)
    return (v*np.exp(-1j*t*e))@v.conj().T
def apply_axis(state,matrix,axis):
    x=np.moveaxis(state,axis,0);shape=x.shape
    return np.moveaxis((matrix@x.reshape(shape[0],-1)).reshape(shape),0,axis)

class MusicalGraph:
    def __init__(self,rhythm_count=16):
        if rhythm_count not in [8,16,32]:raise ValueError('rhythm_count must be8,16,32')
        self.shape=(4,4,4,rhythm_count,8);self.size=int(np.prod(self.shape))
        self.indices=np.array(list(itertools.product(range(4),repeat=3)))
        self.intervals=INTERVALS[self.indices]
        self.degrees=np.column_stack([np.zeros(64,int),np.cumsum(self.intervals,axis=1)])
        allr=np.array([[0]+list(x) for x in itertools.combinations(np.arange(1,8)/2,3)])
        # Deterministic farthest-point coverage, starting from quarter notes.
        selected=[int(np.argmin(np.sum(abs(allr-np.arange(4)),axis=1)))]
        while len(selected)<rhythm_count:
            d=np.min(np.sum(abs(allr[:,None]-allr[selected][None]),axis=2),axis=1)
            d[selected]=-1;selected.append(int(np.argmax(d)))
        self.rhythms=allr[selected]
        self.chord_degrees=np.array([[d,(d+2)%7,(d+4)%7] for d in range(7)]+[[4,0,1]])
        self.chord_names=['I','ii','iii','IV','V','vi','vii','Vsus']
        a=np.zeros((4,4));a[np.arange(3),np.arange(1,4)]=1;a+=a.T
        dr=np.sum(abs(self.rhythms[:,None]-self.rhythms[None]),axis=-1)
        ar=np.zeros((rhythm_count,rhythm_count))
        for i in range(rhythm_count):
            nbr=np.argsort(dr[i])[1:5];ar[i,nbr]=np.exp(-dr[i,nbr]/1.5)
        ar=np.maximum(ar,ar.T);ar/=ar.sum(axis=0).max()
        ah=np.zeros((8,8))
        for i in range(8):
            for j in range(i):
                common=len(set(self.chord_degrees[i])&set(self.chord_degrees[j]))
                ah[i,j]=ah[j,i]=.15+.3*common
        ah/=ah.sum(axis=0).max()
        self.adjacency=[a,a*.87,a*1.13,ar,ah]
        self.hamiltonians=[-x for x in self.adjacency]
        span=np.ptp(self.degrees,axis=1)/6
        direction=self.degrees[:,-1]/6
        sync=np.mean(abs(self.rhythms-np.round(self.rhythms)),axis=1)*2
        tension=np.array([0,.35,.25,.25,.85,.2,.9,.65])
        # These are phase-interaction energies, not optimization objectives.
        self.interaction=(.65*span[:,None,None]*tension[None,None,:]+
            .5*direction[:,None,None]*(tension[None,None,:]-.4)+
            .35*span[:,None,None]*sync[None,:,None]).reshape(self.shape)
        self.cache={}
    def gates(self,duration,steps):
        key=(float(duration),int(steps))
        if key not in self.cache:
            dt=duration/steps
            self.cache[key]=[hermitian_unitary(h,dt) for h in self.hamiltonians]
        return self.cache[key]
    def step(self,state,duration=.55,interaction=.7,feedback=None,steps=64):
        gates=self.gates(duration,steps);dt=duration/steps
        v=interaction*self.interaction
        if feedback is not None:v=v+np.asarray(feedback).reshape(self.shape)
        phase=np.exp(-.5j*dt*v);x=state.copy()
        for _ in range(steps):
            x*=phase
            for axis,u in enumerate(gates):x=apply_axis(x,u,axis)
            x*=phase
        return x
    def initial(self,seed):
        r=np.random.default_rng(np.random.SeedSequence([seed,771]))
        factors=[]
        for size in self.shape:
            factors.append(np.exp(1j*r.uniform(-np.pi,np.pi,size))/np.sqrt(size))
        x=factors[0]
        for f in factors[1:]:x=np.multiply.outer(x,f)
        return x

def probability(state):
    p=abs(state)**2
    return p/p.sum()

def tilt_to_mean(p,d,target):
    """Classical KL-minimal exponential tilt. derivative E[d] is Var[d]."""
    p=np.asarray(p,float).ravel();d=np.asarray(d,float).ravel()
    support=p>1e-280;lo=float(d[support].min());hi=float(d[support].max())
    actual=float(np.clip(target,lo+1e-7,hi-1e-7))
    logp=np.where(p>0,np.log(np.maximum(p,1e-300)),-np.inf) # Preserve exact constraint zeros.
    left,right=-250.,250.
    def law(lam):
        x=logp+lam*d;x-=x.max();q=np.exp(x);return q/q.sum()
    for _ in range(45):
        middle=(left+right)/2;q=law(middle)
        if q@d<actual:left=middle
        else:right=middle
    lam=(left+right)/2;q=law(lam)
    return q,{'requested':float(target),'attainable':[lo,hi],'expected':float(q@d),
              'lambda':lam,'clamped':abs(actual-target)>1e-6}

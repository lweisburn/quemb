import numpy, sys, scipy

def rdm1_fullbasis(self, return_ao=True, only_rdm1=False, only_rdm2=False, return_lo=False, return_RDM2=True):
    from pyscf import scf, ao2mo
    
    C_mo = self.C.copy()
    
    nao, nmo = C_mo.shape
    
    rdm1AO = numpy.zeros((nao, nao))
    rdm2AO = numpy.zeros((nao, nao, nao, nao))
    
    for fobjs in self.Fobjs:

        if return_RDM2:
            drdm1 = fobjs.__rdm1.copy()
            drdm1[numpy.diag_indices(fobjs.nsocc)] -= 2.
            dm_nc = numpy.einsum('ij,kl->ijkl', drdm1, drdm1, dtype=numpy.float64, optimize=True) - \
                0.5*numpy.einsum('ij,kl->iklj', drdm1, drdm1, dtype=numpy.float64,optimize=True)
            fobjs.__rdm2 -= dm_nc

        
        cind = [ fobjs.fsites[i] for i in fobjs.efac[1]]
        Pc_ = fobjs.TA.T @ self.S @ self.W[:, cind] @ self.W[:, cind].T @ self.S @ fobjs.TA

        if not only_rdm2:            
            rdm1_eo = fobjs.mo_coeffs @ fobjs.__rdm1 @ fobjs.mo_coeffs.T                                
            rdm1_center = Pc_ @ rdm1_eo            
            rdm1_ao = fobjs.TA @ rdm1_center @ fobjs.TA.T
            
            # equivalent to tranform full
            #if return_lo:
            #    rdm1_lo = fobjs.C_lo_eo @ rdm1_center @ fobjs.C_lo_eo.T 
            #    rdm1_lo = (rdm1_lo + rdm1_lo.T)/2.
            #    rdm1lo += rdm1_lo
            rdm1AO += rdm1_ao
            
        if not only_rdm1:
            rdm2s = numpy.einsum("ijkl,pi,qj,rk,sl->pqrs", fobjs.__rdm2,
                                 *([fobjs.mo_coeffs]*4),optimize=True)
            rdm2_ao = numpy.einsum('xi,ijkl,px,qj,rk,sl->pqrs',
                                   Pc_, rdm2s, fobjs.TA, fobjs.TA,
                                   fobjs.TA, fobjs.TA, optimize=True)
            #if return_lo:
            #    CloT_S = self.W.T @ self.S
            #    rdm2_lo = numpy.einsum("ijkl,pi,qj,rk,sl->pqrs",
            #                           rdm2_ao, CloT_S, CloT_S,
            #                           CloT_S, CloT_S, optimize=True)
            #    rdm2lo += rdm2_lo
            rdm2AO += rdm2_ao

    if not only_rdm1:        
        rdm2AO = (rdm2AO + rdm2AO.transpose(1,0,3,2))/2
        if return_RDM2:
            nc_AO = numpy.einsum('ij,kl->ijkl', rdm1AO, rdm1AO, dtype=numpy.float64, optimize=True) - \
                numpy.einsum('ij,kl->iklj', rdm1AO, rdm1AO, dtype=numpy.float64, optimize=True)*0.5
            rdm2AO = nc_AO + rdm2AO
        
        if not return_ao:
            CmoT_S = self.C.T @ self.S
            rdm2MO = numpy.einsum("ijkl,pi,qj,rk,sl->pqrs",
                                  rdm2AO, CmoT_S, CmoT_S,
                                  CmoT_S, CmoT_S, optimize=True)
        if return_lo:
            CloT_S = self.W.T @ self.S
            rdm2LO = numpy.einsum("ijkl,pi,qj,rk,sl->pqrs",
                                  rdm2AO, CloT_S, CloT_S,
                                  CloT_S, CloT_S, optimize=True)
                
    if not only_rdm2:
        rdm1AO = (rdm1AO + rdm1AO.T)/2.
        if not return_ao: rdm1MO = self.C.T @ self.S @ rdm1AO @ self.S @ self.C
        if return_lo: rdm1LO = self.W.T @ self.S @ rdm1AO @ self.S @ self.W

    if return_RDM2:
        Eh1 = numpy.einsum('ij,ij', self.hcore, rdm1AO, optimize=True)
        eri = ao2mo.restore(1,self.mf._eri, self.mf.mo_coeff.shape[1])
        E2 = 0.5*numpy.einsum('pqrs,pqrs', eri,rdm2AO, optimize=True)
        print(flush=True)    
        print('-----------------------------------------------------',
              flush=True)
        print(' BE ENERGIES with cumulant-based expression', flush=True)
        
        print('-----------------------------------------------------',
              flush=True)
        
        print(' 1-elec E        : {:>15.8f} Ha'.format(Eh1), flush=True)
        print(' 2-elec E        : {:>15.8f} Ha'.format(E2), flush=True)
        E_tot = Eh1+E2+self.E_core + self.enuc
        print(' E_BE            : {:>15.8f} Ha'.format(E_tot), flush=True)
        print(' Ecorr BE        : {:>15.8f} Ha'.format((E_tot)-self.ebe_hf), flush=True)
        print('-----------------------------------------------------',
          flush=True)
    
        print(flush=True)
    
    if only_rdm1:
        if return_ao:
            return rdm1AO
        else:
            return rdm1MO
    if only_rdm2:
        if return_ao:
            return rdm2AO
        else:
            return rdm2MO

    if return_lo and return_ao: return (rdm1AO, rdm2AO, rdm1LO, rdm2LO)
    if return_lo and not return_ao: return (rdm1MO, rdm2MO, rdm1LO, rdm2LO)

    if return_ao: return rdm1AO, rdm2AO
    if not return_ao: return rdm1MO, rdm2MO

def get_rdm(self, approx_cumulant=False, use_full_rdm=False, return_ao=True):
    from pyscf import scf, ao2mo
    
            
    rdm1f, Kumul, rdm1_lo, rdm2_lo = self.rdm1_fullbasis(return_lo=True, return_RDM2=False)

    
    hcore_lo = self.W.T @ self.hcore @ self.W
    Eh1_lo = numpy.einsum('ij,ij', hcore_lo, rdm1_lo, optimize=True)
    print('Eh1 LO ', Eh1_lo)
    if not approx_cumulant:

        #for fobjs in self.Fobjs:
        #    drdm1 = fobjs.__rdm1.copy()
        #    drdm1[numpy.diag_indices(fobjs.nsocc)] -= 2.
        #    dm_nc = numpy.einsum('ij,kl->ijkl', drdm1, drdm1, dtype=numpy.float64, optimize=True) - \
        #        0.5*numpy.einsum('ij,kl->iklj', drdm1, drdm1, dtype=numpy.float64,optimize=True)
        #    fobjs.__rdm2 -= dm_nc
        Kumul_T = self.rdm1_fullbasis(only_rdm2=True)
        if use_full_rdm:
            RDM2_full =  numpy.einsum('ij,kl->ijkl', rdm1f, rdm1f, dtype=numpy.float64, optimize=True) - \
                numpy.einsum('ij,kl->iklj', rdm1f, rdm1f, dtype=numpy.float64, optimize=True)*0.5
            RDM2_full += Kumul_T

    del_gamma = rdm1f - self.hf_dm        
    veff = scf.hf.get_veff(self.mol, rdm1f, hermi=0)
    Eh1 = numpy.einsum('ij,ij', self.hcore, rdm1f, optimize=True)
    EVeff = numpy.einsum('ij,ij',veff, rdm1f, optimize=True)

    Eh1_dg = numpy.einsum('ij,ij',self.hcore, del_gamma, optimize=True)
    Eveff_dg = numpy.einsum('ij,ij',self.hf_veff, del_gamma, optimize=True)
    
    eri = ao2mo.restore(1,self.mf._eri, self.mf.mo_coeff.shape[1])
    EKumul = numpy.einsum('pqrs,pqrs', eri,Kumul, optimize=True)
    EKumul_T = numpy.einsum('pqrs,pqrs', eri,Kumul_T, optimize=True)
    if use_full_rdm:
        E2 = numpy.einsum('pqrs,pqrs', eri,RDM2_full, optimize=True)
        
    EKapprox = self.ebe_hf + Eh1_dg + Eveff_dg + EKumul/2. 
    EKtrue = Eh1 + EVeff/2. + EKumul_T/2. + self.enuc + self.E_core
    
    print(flush=True)    
    print('-----------------------------------------------------',
          flush=True)
    print(' BE ENERGIES with cumulant-based expression', flush=True)
    
    print('-----------------------------------------------------',
          flush=True)
    print(' E_BE = E_HF + Tr(F del g) + Tr(V K_approx)', flush=True)
    print(' E_HF            : {:>12.8f} Ha'.format(self.ebe_hf), flush=True)
    print(' Tr(F del g)     : {:>12.8f} Ha'.format(Eh1_dg+Eveff_dg), flush=True)
    print(' Tr(V K_aprrox)  : {:>12.8f} Ha'.format(EKumul/2.), flush=True)
    print(' E_BE            : {:>12.8f} Ha'.format(EKapprox), flush=True)
    print(' Ecorr BE        : {:>12.8f} Ha'.format(EKapprox-self.ebe_hf), flush=True)
    print(flush=True)
    print(' E_BE = Tr(F[g] g) + Tr(V K_true)', flush=True)
    print(' Tr(h1 g)        : {:>12.8f} Ha'.format(Eh1), flush=True)
    print(' Tr(Veff[g] g)   : {:>12.8f} Ha'.format(EVeff/2.), flush=True)
    print(' Tr(V K_true)    : {:>12.8f} Ha'.format(EKumul_T/2.), flush=True)
    print(' E_BE            : {:>12.8f} Ha'.format(EKtrue), flush=True)
    if use_full_rdm:
        
        print(' E(g+G)          : {:>12.8f} Ha'.format(Eh1 + 0.5*E2 + self.E_core + self.enuc),
                           flush=True)
    print(' Ecorr BE        : {:>12.8f} Ha'.format(EKtrue-self.ebe_hf), flush=True)
    print(flush=True)
    print(' True - approx   : {:>12.4e} Ha'.format(EKtrue-EKapprox))
    print('-----------------------------------------------------',
          flush=True)
    
    print(flush=True)

    if return_ao: return(rdm1f, RDM2_full)
    rdm1f, Kumul = self.rdm1_fullbasis(return_ao =False)    
    Kumul_T = self.rdm1_fullbasis(only_rdm2=True, return_ao=False)
    
    RDM2_full =  numpy.einsum('ij,kl->ijkl', rdm1f, rdm1f, optimize=True) - \
        numpy.einsum('ij,kl->iklj', rdm1f, rdm1f, optimize=True)*0.5
    RDM2_full += Kumul_T
    
    return(rdm1f, RDM2_full)

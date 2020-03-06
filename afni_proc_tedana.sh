

python2.7 afni_proc.py -subj_id 503                                    \
                  -blocks tshift align tlrc volreg mask combine \
                          blur scale regress                    \
                  -copy_anat mp2rage_ws.nii.gz                     \
                  -dsets_me_run TMII_XNAT_E29799_rest_e*.nii    \
                  -echo_times 14.0 37.87 61.74                  \
                  -reg_echo 2                                   \
                  -tcat_remove_first_trs 2                      \
                  -align_opts_aea -cost lpc+ZZ                  \
                  -tlrc_base MNI152_T1_1mm.nii.gz               \
                  -tlrc_NL_warp                                 \
                  -volreg_align_to MIN_OUTLIER                  \
                  -volreg_align_e2a                             \
                  -volreg_tlrc_warp                             \
                  -mask_epi_anat yes                            \
                  -combine_method tedana                        \
                  -regress_motion_per_run                       \
                  -regress_censor_motion 0.2                    \
                  -regress_censor_outliers 0.05                 \
                  -regress_apply_mot_types demean deriv         \
                  -regress_est_blur_epits


